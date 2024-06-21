from xml.etree.ElementTree import fromstring, Element
from dataclasses import dataclass
from copy import deepcopy

from typing import Self, Iterable
import sys

from string_theory.condition import Condition
from string_theory.testing import ObservableTestSuite
from string_theory.utils import generate_with_retries, read_bnf

from .correct import Config as CorrectConfig
from .wacky import (
    Config as WackyConfig,
    ConfigError,
    bug_recursion_limit,
    bug_removed_orphan_twice,
    bug_zero_div_cost,
    bug_zero_div_orphans,
)
from .console import Console

from isla.language import parse_isla
from isla.isla_predicates import COUNT_PREDICATE, IN_TREE_PREDICATE, SAME_POSITION_PREDICATE
from isla.solver import ISLaSolver


SAMPLE = '''
<build>
	<task id="main_task" main="true">
		<dep id="sub_task"></dep>
		<step cost="12">sudo rm -rf</step>
		<step script="./step1.sh" cost="30"></step>
	</task>
	
	<task id="sub_task">
		<step cost="1">echo hello</step>
	</task>
</build>
'''

def run_sample():
    CorrectConfig.parse(SAMPLE).build()

CONFIG_GRAMMAR = read_bnf('examples/config.bnf')

ID_DEF_USE_ISLA = '''
forall <dep>="(dep id='{<id> dep_id}'/)" in start:
    exists <task>="(task id='{<id> task_id}'<mb-main>)<deps><steps>(/task)":
        (dep_id = task_id)
'''

ID_DEF_USE = parse_isla(ID_DEF_USE_ISLA, CONFIG_GRAMMAR)

NO_SELF_DEP_ISLA = '''
forall <dep> d="(dep id='{<id> dep_id}'/)" in start:
    exists <task> t="(task id='{<id> task_id}'<mb-main>)<deps><steps>(/task)":
        ((dep_id = task_id) and (not (inside(d, t))))
'''

NO_SELF_DEP = parse_isla(NO_SELF_DEP_ISLA, CONFIG_GRAMMAR, structural_predicates={IN_TREE_PREDICATE})

ONE_MAIN_ISLA = '''
forall <build> build in start:
    (count(build, <main-true>, "1"))
'''

ONE_MAIN = parse_isla(ONE_MAIN_ISLA, CONFIG_GRAMMAR, structural_predicates={COUNT_PREDICATE})

ONE_MAIN_QUANT_ISLA = '''
(forall <main-true> a in start:
    forall <main-true> b in start:
        (same_position(a, b)
    )
)
and
(exists <mb-main> main in start:
    (main = " main='true'"))
'''

ONE_MAIN_QUANT = parse_isla(ONE_MAIN_QUANT_ISLA, CONFIG_GRAMMAR, structural_predicates={SAME_POSITION_PREDICATE})

UNIQUE_IDS_ISLA = '''
forall <task>="(task id='{<id> task_id}'<mb-main>)<deps><steps>(/task)":
    (not (exists <task> other="(task id='{<id> other_task_id}')<deps><steps>(/task)":
        (task_id = other_task_id)
    ))
'''

UNIQUE_IDS = parse_isla(UNIQUE_IDS_ISLA, CONFIG_GRAMMAR)

NO_ORPHANS_ISLA = '''
forall <task>="(task id='{<id> task_id}'<mb-main>)<deps><steps>(/task)":
    exists <dep> d="(dep id='{<id> dep_id}'/)":
        (dep_id = task_id)
'''

NO_ORPHANS = parse_isla(NO_ORPHANS_ISLA, CONFIG_GRAMMAR)

CONFIG_FORMULA = ID_DEF_USE & NO_SELF_DEP & UNIQUE_IDS & NO_ORPHANS & ONE_MAIN_QUANT

### --- TESTING ---

def test_input_with_reference(inp: str):
    reference = ...

def eval_crash():
    INPUTS_PER_TEST = 200
    TESTS_PER_CONDITION = 1
    formulae = [ID_DEF_USE, (-NO_SELF_DEP), UNIQUE_IDS, NO_ORPHANS, ONE_MAIN_QUANT]
    conditions = [
        bug_zero_div_orphans,
        bug_zero_div_cost,
        bug_recursion_limit,
        bug_removed_orphan_twice,
    ]

    formula = ID_DEF_USE & UNIQUE_IDS

    for condition in conditions:
        test_benchmarks = []
        constraint = None
        print(f'\n[TEST: {condition.description}]')
        for formula in formulae:
            constraint = formula
            tests_to_failure = []
            for _ in range(TESTS_PER_CONDITION):
                solver = ISLaSolver(CONFIG_GRAMMAR, constraint)
                inputs = generate_with_retries(solver)
                console = Console()

                for num, inp in zip(range(1, INPUTS_PER_TEST + 1), inputs):
                    condition.reset()
                    WackyConfig.injected_bug = condition
                    try:
                        # print(inp)
                        WackyConfig.parse(inp.to_string(), silent=False, strict=True)\
                            .build()\
                            .run(console)
                    except ConfigError as e:
                        pass
                    except Exception as e:
                        if condition.was_triggered:
                            tests_to_failure.append(num)
                            break
                        else:
                            print(f'Found irrelevant exception {e}')
                else:
                    tests_to_failure.append(None)
            test_benchmarks.append((constraint, tests_to_failure))
            print(formulae.index(constraint), tests_to_failure)


if __name__ == '__main__':
    command = sys.argv[1]
    match command:
        case 'crash':
            eval_crash()
        case 'sample':
            run_sample()
        case _:
            print('Unknown command')