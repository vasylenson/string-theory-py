from xml.etree.ElementTree import fromstring, Element
from dataclasses import dataclass
from copy import deepcopy

from typing import Self, Iterable

from string_theory.condition import Condition
from string_theory.testing import ObservableTestSuite
from string_theory.utils import generate_with_retries, read_bnf

from isla_formalizations.xml_lang import XML_GRAMMAR
from isla.language import parse_isla
from isla.isla_predicates import DIRECT_CHILD_PREDICATE, COUNT_PREDICATE, IN_TREE_PREDICATE, SAME_POSITION_PREDICATE
from isla.solver import ISLaSolver


class ConfigError(Exception):
    pass


@dataclass
class Command:
    text: str

    def run(self):
        print('$', self.text)


@dataclass
class Script:
    text: str

    def run(self):
        print('source', self.text)

    

@dataclass
class Task:
    id: str
    is_main: bool
    steps: list[tuple[Command | Script, int]]
    dep_ids: list[str]
    deps: set[Self] | None = None


def br_to_xml(br: str):
    for old, new in [("'", '"'), ('(', '<'), (')', '>')]:
        br = br.replace(old, new)
    return br



class Config:
    EL_BUILD = 'build'
    EL_TASK = 'task'
    EL_STEP = 'step'
    EL_DEP = 'dep'

    def __init__(self, tasks: Iterable[Task], main: Task) -> None:
        self.tasks = tasks
        self.main = main

    def build(self):
        total_cost = self.perform(self.main)
        print('Finished with total cost', total_cost)
    
    def perform(self, task: Task) -> int:
        cost = 0

        for dep in task.deps:
            cost += self.perform(dep)
    
        
        for (step, step_cost) in task.steps:
            step.run()
            cost += step_cost
        
        return cost

    @classmethod
    def parse(cls, text: str, strict: bool = False):
        warn = throw_config_error if strict else print
        xml = fromstring(br_to_xml(text))

        if xml.tag != cls.EL_BUILD:
            raise ConfigError('The root must be a <build> element.')
        
        # parse tasks
        tasks: dict[str, Task] = {}
        for task in xml:
            if task.tag != cls.EL_TASK:
                warn('<build> should only contain <task> elements.')

                continue

            task = cls._parse_task_data(task, strict)

            if task.id in tasks:
                warn(f"Found tasks with the same id={task.id}")

            tasks[task.id] = task
        
        # link dependencies and finding main task
        main = None
        for task in tasks.values():
            if task.is_main:
                if main is None:
                    main = task
                else:
                    warn('There should only be one main <task>')
                    
            deps = []
            for dep_id in task.dep_ids:
                if dep_id not in tasks:
                    warn('<dep> pointing to an unknown task')
                    
                    continue

                deps.append(tasks[dep_id])
            
            task.deps = deps
        
        if main is None:
            warn('There should be a main task')
        
        return cls(tasks, main or list(tasks.values())[0])
        
    @classmethod
    def _parse_task_data(cls, task: Element, strict: bool = False):
        warn = throw_config_error if strict else print

        if 'id' not in task.attrib:
            raise ConfigError('<task> must have an ID.')

        task_id = task.attrib['id']
        is_main = 'main' in task.attrib and task.attrib['main'] == 'true'

        dep_ids = []
        steps = []
        for el in task:
            if el.tag == cls.EL_DEP:
                if el.text is not None and el.text != '':
                    warn('<dep> should have no contents')
                
                dep_ids.append(el.attrib['id'])
            elif el.tag == cls.EL_STEP:
                if 'cost' not in el.attrib:
                    warn('<step> should have a cost')

                try:
                    step_cost = int(el.attrib['cost'])
                except ValueError:
                    raise ConfigError('<step> cost should be an integer')

                has_command = el.text is not None and el.text != ''
                has_script = 'script' in el.attrib and el.attrib['script'] != ''

                if not (has_command ^ has_script):
                    warn('<step> should either have a command or a script')
                
                if has_command:
                    steps.append((Command(el.text), step_cost))
                elif has_script:
                    steps.append((Script(el.attrib['script']), step_cost))

            else:
                if strict:
                    raise ConfigError(f'Unexpected tag <{el.tag}> in <task>')

        return Task(id=task_id, is_main=is_main, steps=steps, dep_ids=dep_ids)
    
def throw_config_error(message):
    raise ConfigError(message)

CONFIG_GRAMMAR = read_bnf('examples/config.bnf')

ID_DEF_USE_ISLA = '''
forall <dep>="(dep id='{<id> dep_id}'/)" in start:
    exists <task>="(task id='{<id> task_id}')<deps><steps>(/task)":
        (dep_id = task_id)
'''

ID_DEF_USE = parse_isla(ID_DEF_USE_ISLA, CONFIG_GRAMMAR)

NO_SELF_DEP_ISLA = '''
forall <dep> d="(dep id='{<id> dep_id}'/)" in start:
    exists <task> t="(task id='{<id> task_id}')<deps><steps>(/task)":
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
forall <task>="(task id='{<id> task_id}')<deps><steps>(/task)":
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

inputs = generate_with_retries(ISLaSolver(CONFIG_GRAMMAR, CONFIG_FORMULA))