from xml.etree.ElementTree import fromstring, Element
from dataclasses import dataclass
from copy import deepcopy

from typing import Self, Iterable
import sys
from time import time

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
from isla.isla_predicates import COUNT_PREDICATE, IN_TREE_PREDICATE, SAME_POSITION_PREDICATE, DIRECT_CHILD_PREDICATE
from isla.solver import ISLaSolver
from isla_formalizations.xml_lang import XML_GRAMMAR

XML_TAGS = '''
# matching open and close XML tags
(forall <xml-tree> tree="<{<id> opid}[ <xml-attribute>]><inner-xml-tree></{<id> clid}>" in start:
    (= opid clid))
'''
XML_FORMULA = parse_isla(XML_TAGS, XML_GRAMMAR)

CORRECT_TAGS_ISLA = '''
# correct tag IDs
(<xml-open-tag>.<id> = "build" or <xml-open-tag>.<id> = "task" or <xml-open-tag>.<id> = "step") and (<xml-openclose-tag>.<id> = "dep")
'''
CORRECT_TAGS = parse_isla(CORRECT_TAGS_ISLA, XML_GRAMMAR)

CORRECT_ATTRS_ISLA = '''
# correct attribute IDs
<xml-attribute>.<id> = "id" or <xml-attribute>.<id> = "main" or <xml-attribute>.<id> = "cost" or <xml-attribute>.<id> = "script"
'''
CORRECT_ATTRS = parse_isla(CORRECT_ATTRS_ISLA, XML_GRAMMAR)

BUILD_TAG_ISLA = '''
# the build tag at the top level
(exists <xml-tree> root="<{<id> id}>{<inner-xml-tree> inside}<xml-close-tag>" in start: (id = "build"))
and
(forall <xml-tree> root="<{<id> id}[ <xml-attribute>]><inner-xml-tree><xml-close-tag>" in start: (
    (id = "build") implies direct_child(root, start)))
'''
BUILD_TAG = parse_isla(BUILD_TAG_ISLA, XML_GRAMMAR, structural_predicates={DIRECT_CHILD_PREDICATE})

STEP_TEXT_ISLA = '''
# only steps may contain text
(forall <xml-tree> command="<{<id> id}><text><xml-close-tag>" in start: (id = "step"))
'''
STEP_TEXT = parse_isla(STEP_TEXT_ISLA, XML_GRAMMAR)

STEP_INSIDE_TASK_ISLA = '''
# <step> is always inside <task>
(forall <xml-tree> step="<{<id> step_id}[ <xml-attribute>]><inner-xml-tree><xml-close-tag>" in start: (
    (step_id = "step") implies
    (exists <xml-tree> task="<{<id> task_id}[ <xml-attribute>]><inner-xml-tree><xml-close-tag>":
        (task_id = "task" and inside(step, task)))))
'''
STEP_INSIDE_TASK = parse_isla(STEP_INSIDE_TASK_ISLA, XML_GRAMMAR, structural_predicates={IN_TREE_PREDICATE})

DEP_INSIDE_TASK_ISLA = '''
# <dep> is always inside <task>
(forall <xml-tree> dep="<{<id> dep_id}[ <xml-attribute>]/>" in start: (
    (dep_id = "dep") implies
    (exists <xml-tree> task="<{<id> task_id}[ <xml-attribute>]><inner-xml-tree><xml-close-tag>":
        (task_id = "task" and inside(dep, task)))))
'''
DEP_INSIDE_TASK = parse_isla(DEP_INSIDE_TASK_ISLA, XML_GRAMMAR, structural_predicates={IN_TREE_PREDICATE})

schema_formula = '''
(forall <xml-tree> el_1="<{<id> el_1_id}[ <xml-attribute>]><inner-xml-tree><xml-close-tag>" in start:
    forall <xml-tree> el_2="<{<id> el_2_id}[ <xml-attribute>]><inner-xml-tree><xml-close-tag>" in start:
    (inside(el_1, el_2) implies (not (el_1_id = el_2_id))))
'''
# and

# (exists <tag-id> task_id: (task_id = "task") )
# forall <tag-id> step_id="step" in start:
#     exists <xml-tree> task="<{<tag-id> task_id}[ <xml-attribute>]>{<inner-xml-tree> inner}<xml-close-tag>" in start:
#         (task_id = "task" and inside(step_id, inner))

cf = [
    None,
    XML_FORMULA,
    CORRECT_TAGS,
    CORRECT_ATTRS,
    BUILD_TAG,
    STEP_TEXT,
    STEP_INSIDE_TASK,
    DEP_INSIDE_TASK,
]
def bench(constraints = cf, grammar = XML_GRAMMAR, print_examples = True, only = None):
    formula = None

    targets = [1, 10, 100]
    print('\t'.join((str(t) for t in targets)))
    for constraint in constraints:
        if formula is None:
            formula = constraint
        else:
            formula = formula & constraint

        if only is not None and constraint is not only:
            continue

        for n in targets:

            inputs = generate_with_retries(ISLaSolver(grammar, formula))
            start = time()
            for i in range(n):
                next(inputs)
            print((time() - start) // 0.001 * 0.001, end='\t')

        print('\t\t', next(inputs) if print_examples else '')


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
forall <dep> d="(dep id='{<id> dep_id}'/)":
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
        (same_position(a, b)))
and (exists <mb-main> main in start:
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
forall <task>="(task id='{<id> task_id}')<deps><steps>(/task)":
    exists <dep> d="(dep id='{<id> dep_id}'/)":
        (dep_id = task_id)
'''

NO_ORPHANS = parse_isla(NO_ORPHANS_ISLA, CONFIG_GRAMMAR)

CONFIG_FORMULA = ID_DEF_USE & NO_SELF_DEP & UNIQUE_IDS & NO_ORPHANS & ONE_MAIN_QUANT

### --- TESTING ---

cs = [
    None,
    UNIQUE_IDS,
    ID_DEF_USE,
    ONE_MAIN_QUANT,
    NO_SELF_DEP,
    NO_ORPHANS,
]

def eval_crash():
    INPUTS_PER_TEST = 1000
    TESTS_PER_CONDITION = 5
    _formulae = [
        None,
        ID_DEF_USE,
        ONE_MAIN_QUANT,
        UNIQUE_IDS,
        NO_SELF_DEP,
        NO_ORPHANS,
    ]
    conditions = [
        (bug_zero_div_orphans, _formulae),
        (bug_zero_div_cost, _formulae),
        (bug_recursion_limit, [None, ID_DEF_USE, UNIQUE_IDS, -NO_SELF_DEP,]),
        # (bug_removed_orphan_twice, [None, ID_DEF_USE & ONE_MAIN_QUANT, -NO_ORPHANS,]),
    ]

    for condition, formulae in conditions:
        benchmarks = []
        constraint = None
        print(f'\n[TEST: {condition.description}]')
        for fi, formula in enumerate(formulae):
            if constraint is None:
                constraint = formula
            else:
                constraint = formula & constraint
            tests_to_failure = []
            times_to_failure = []
            for _ in range(TESTS_PER_CONDITION):
                solver = ISLaSolver(CONFIG_GRAMMAR, constraint)
                inputs = generate_with_retries(solver)
                console = Console()

                start = time()
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
                            times_to_failure.append(time() - start)
                            tests_to_failure.append(num)
                            break
                        else:
                            print(f'Found irrelevant exception {e}')
                else:
                    tests_to_failure.append(None)
                    times_to_failure.append(None)
            benchmarks.append((tests_to_failure, times_to_failure))
            print(tests_to_failure, times_to_failure, '\n', mean(tests_to_failure), mean(times_to_failure), '\n')
            # if all(n == 1 for n in tests_to_failure):
            #     break

def mean(inputs: list):
    samples = (i for i in inputs if i is not None)
    return sum(samples) / len(samples)

if __name__ == '__main__':
    command = sys.argv[1]
    match command:
        case 'crash':
            eval_crash()
        case 'sample':
            run_sample()
        case 'cf':
            bench(cf, XML_GRAMMAR)
        case 'cs':
            bench(cs, CONFIG_GRAMMAR, print_examples=False, only=NO_ORPHANS)
        case _:
            print('Unknown command')