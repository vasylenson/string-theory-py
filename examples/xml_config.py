from xml.etree.ElementTree import fromstring, Element
from dataclasses import dataclass
from copy import deepcopy

from typing import Self, Iterable

from string_theory.condition import Condition
from string_theory.utils import generate_until_absolutely_cannot_anymore

from isla_formalizations.xml_lang import XML_GRAMMAR
from isla.language import parse_isla
from isla.isla_predicates import DIRECT_CHILD_PREDICATE, COUNT_PREDICATE, IN_TREE_PREDICATE
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
        xml = fromstring(text)

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
        
        return cls(tasks, main or tasks[0])
        
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

CONFIG_GRAMMAR = deepcopy(XML_GRAMMAR)
CONFIG_GRAMMAR.update({
    "<xml-open-tag>": ["<<tag-id> <xml-attribute>>", "<<tag-id>>"],
    "<xml-openclose-tag>": ["<<tag-id> <xml-attribute>/>", "<<tag-id>/>"],
    "<xml-close-tag>": ["</<tag-id>>"],
    "<xml-attribute>": ["<xml-attribute> <xml-attribute>", '<attr-id>="<text>"'],
    "<tag-id>": ["build", "task", "step", "dep"],
    "<attr-id>": ["id", "cost", "main", "script"],
})

for removed in ["<id>", "<id-start-char>",  "<id-chars>",  "<id-char>"]:
    CONFIG_GRAMMAR.pop(removed)

xml_config_isla = r'''
(forall <xml-tree> tree="<{<tag-id> opid}[ <xml-attribute>]><inner-xml-tree></{<tag-id> clid}>" in start:
    (= opid clid))
and
(<xml-openclose-tag>.<tag-id> = "dep")
'''

CONFIG_FORMULA = parse_isla(xml_config_isla, CONFIG_GRAMMAR)

schema_formula = '''
# the build tag
(exists <xml-tree> root="<{<tag-id> id}>{<inner-xml-tree> inside}<xml-close-tag>" in start: (id = "build"))
and
(forall <xml-tree> root="<{<tag-id> id}[ <xml-attribute>]><inner-xml-tree><xml-close-tag>" in start: (
    (id = "build") implies direct_child(root, start)
))
and

# only deps are self-closing
(forall <xml-tree> dep="<{<tag-id> id}[ <xml-attribute>]/>" in start: (id = "dep"))
and

# only steps may contain text
(forall <xml-tree> command="<{<tag-id> id}><text><xml-close-tag>" in start: (id = "step"))
and

(forall <xml-tree> step="<{<tag-id> step_id}[ <xml-attribute>]><inner-xml-tree><xml-close-tag>" in start: (
    (step_id = "step") implies
    (exists <xml-tree> task="<{<tag-id> task_id}[ <xml-attribute>]><inner-xml-tree><xml-close-tag>":
        (task_id = "task" and inside(step, task))
    )
))
and

(forall <xml-tree> dep="<{<tag-id> dep_id}[ <xml-attribute>]/>" in start: (
    (dep_id = "dep") implies
    (exists <xml-tree> task="<{<tag-id> task_id}[ <xml-attribute>]><inner-xml-tree><xml-close-tag>":
        (task_id = "task" and inside(dep, task))
    )
))
and

(forall <xml-tree> el_1="<{<tag-id> el_1_id}[ <xml-attribute>]><inner-xml-tree><xml-close-tag>" in start:
    forall <xml-tree> el_2="<{<tag-id> el_2_id}[ <xml-attribute>]><inner-xml-tree><xml-close-tag>" in start:
    (inside(el_1, el_2) implies (not (el_1_id = el_2_id)))
)
# and

# (exists <tag-id> task_id: (task_id = "task") )
# forall <tag-id> step_id="step" in start:
#     exists <xml-tree> task="<{<tag-id> task_id}[ <xml-attribute>]>{<inner-xml-tree> inner}<xml-close-tag>" in start:
#         (task_id = "task" and inside(step_id, inner))
'''

SCHEMA_FORMULA = parse_isla(schema_formula, CONFIG_GRAMMAR, structural_predicates={DIRECT_CHILD_PREDICATE, IN_TREE_PREDICATE, COUNT_PREDICATE})

config_src = '''
<build>
	<task id="main_task" main="true">
		<dep id="sub_task"/>
		<step cost="12">sudo rm -rf</step>
		<step script="./step1.sh" cost="30"></step>
	</task>
	
	<task id="sub_task">
		<step cost="1">echo hello</step>
	</task>
</build>
'''

xml = Config.parse(config_src)
xml.build()

solver = ISLaSolver(CONFIG_GRAMMAR, CONFIG_FORMULA & SCHEMA_FORMULA)

for _ in range(100):
    print(solver.solve())