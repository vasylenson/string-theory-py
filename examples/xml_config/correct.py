from xml.etree.ElementTree import fromstring, Element
from dataclasses import dataclass

from typing import Self, Iterable

from string_theory.condition import Condition


c_repeating_id = Condition('Found repeating IDs')
c_circular_dependencies = Condition('There was a circular dependency')
c_missing_dependencies = Condition('For a dependency, no task with matching ID was found')
c_multiple_entry_points = Condition('Multiple tasks are marked an entry point')
c_no_entry_points = Condition('No tasks are an entry point')
c_orphaned_tasks = None and Condition('No tasks are an entry point')


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
        try:
            total_cost = self.perform(self.main)
            print('Finished with total cost', total_cost)
        except RecursionError:
            c_circular_dependencies.trigger()
            print('Failed most likely due to circular dependency')
    
    def perform(self, task: Task) -> int:
        cost = 0

        for dep in task.deps:
            cost += self.perform(dep)
    
        
        for (step, step_cost) in task.steps:
            step.run()
            cost += step_cost
        
        return cost

    @classmethod
    def parse(cls, text: str, strict: bool = False, silent: bool = False):
        warn = (lambda _: ...) if silent else throw_config_error if strict else print
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
                c_repeating_id.trigger()
                warn(f"Found tasks with the same id={task.id}")

            tasks[task.id] = task
        
        # link dependencies and finding main task
        main = None
        for task in tasks.values():
            if task.is_main:
                if main is None:
                    main = task
                else:
                    c_multiple_entry_points.trigger()
                    warn('There should only be one main <task>')
                    
            deps = []
            for dep_id in task.dep_ids:
                if dep_id not in tasks:
                    c_missing_dependencies.trigger()
                    warn('<dep> pointing to an unknown task')
                    
                    continue

                deps.append(tasks[dep_id])
            
            task.deps = deps
        
        if main is None:
            c_no_entry_points.trigger()
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