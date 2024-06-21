from xml.etree.ElementTree import fromstring, Element
from dataclasses import dataclass

from typing import Self, Iterable

from string_theory.condition import Condition

from .console import Console


bug_zero_div_orphans = Condition('Injected bug: calculating the relative number of lone orphan tasks')
bug_zero_div_cost = Condition('Injected bug: calculating the relative cost of task')
bug_recursion_limit = Condition('Injected bug: infinite recursion when building a task sequence')
bug_removed_orphan_twice = Condition('Injected bug: task removed from the set twice')
bug_no_main = Condition('Injected bug: no main')

class ConfigError(Exception):
    pass


@dataclass
class Command:
    text: str

    def run(self):
        return f'$ {self.text}'


@dataclass
class Script:
    text: str

    def run(self) -> str:
        return f'source {self.text}'

    

@dataclass
class Task:
    id: str
    is_main: bool
    steps: list[tuple[Command | Script, int]]
    dep_ids: list[str]
    deps: set[Self] | None = None

    def __hash__(self) -> int:
        return hash(self.id)


def br_to_xml(br: str):
    for old, new in [("'", '"'), ('(', '<'), (')', '>')]:
        br = br.replace(old, new)
    return br



class Config:
    EL_BUILD = 'build'
    EL_TASK = 'task'
    EL_STEP = 'step'
    EL_DEP = 'dep'

    injected_bug: Condition | None = None

    def __init__(self, tasks: Iterable[Task], main: Task) -> None:
        self.tasks = tasks
        self.main = main
        self.steps: list[Task] | None = None

    def build(self) -> Self:
        step_list = self.list_steps(self.main)
        step_list.reverse()

        orphans = set(self.tasks)
        self.steps = []
        for step in step_list:
            with bug_removed_orphan_twice:
                if self.__class__.injected_bug is bug_removed_orphan_twice:
                    #BUG: tasks that are depended on by multiple tasks will be removed multiple times
                    orphans.remove(step)
                else:
                    if step in orphans:
                        orphans.remove(step)

            if step not in self.steps:
                self.steps.append(step)
        
        with bug_zero_div_orphans:
            #BUG: (injected) this will trigger a division by zero
            full_orphans = [orphan for orphan in orphans if len(orphan.deps) == 0]
            if self.__class__.injected_bug == bug_zero_div_orphans:
                relative_full_orphans = len(full_orphans) / len(orphans)

        return self

    def list_steps(self, task: Task) -> list[Task]:
        deps = None
        with bug_no_main:
            #BUG: task will be None if there was no main
            deps = task.deps

        steps = [task]
        for dep in deps:

            with bug_recursion_limit:
                #BUG: This might result in a recursion exception
                if self.__class__.injected_bug is bug_recursion_limit:
                    steps.extend(self.list_steps(dep))
                else:
                    try:
                        steps.extend(self.list_steps(dep))
                    except RecursionError:
                        throw_config_error('Config contains infinite recursion')
        return steps

    def run(self, console: Console | None = None):
        if self.steps is None:
            self.build()
        
        total_cost = 0
        for task in self.steps:
            for step, cost in task.steps:
                output = step.run()
                if console is None:
                    console.log(output)
                total_cost += cost
                with bug_zero_div_cost:
                    #BUG: if the first cost is 0
                    if self.__class__.injected_bug is bug_zero_div_cost:
                        relative_cost = cost / total_cost

        console.log(f'Finished with total cost {total_cost}')


    @classmethod
    def parse(cls, text: str, strict: bool = False, silent: bool = False):
        warn = (lambda _: ...) if silent else throw_config_error if strict else print
        xml = fromstring(br_to_xml(text))

        if xml.tag != cls.EL_BUILD:
            raise ConfigError('The root must be a <build> element.')
        
        # parse tasks
        ids: list[str] = []  # should be sorted
        tasks: list[Task] = []  # should be in the order corresponding to ids
        for task in xml:
            if task.tag != cls.EL_TASK:
                warn('<build> should only contain <task> elements.')
                continue

            task = cls._parse_task_data(task, strict)

            swap = task.id
            new_id_index = None
            for i in range(len(ids)):
                if task.id < ids[i]:
                    continue

                if new_id_index is None:
                    new_id_index = i

                ids[i], swap = swap, ids[i]
            ids.append(swap)

            if new_id_index is None:
                new_id_index = 0
            
            swap = task
            for i in range(len(tasks)):
                if i < new_id_index:
                    continue

                tasks[i], swap = swap, tasks[i]
            tasks.append(swap)
            
        
        # link dependencies and finding main task
        main = None
        for task in tasks:
            if task.is_main:
                if main is None:
                    main = task
                else:
                    warn('There should only be one main <task>')
                    
            deps = []
            for dep_id in task.dep_ids:
                # if dep_id not in ids:
                #     c_missing_dependencies.trigger()
                #     warn('<dep> pointing to an unknown task')
                    
                    # continue
                
                dep_task_index = None
                for i in range(len(ids)):
                    if ids[i] == dep_id:
                        dep_task_index = i
                        break
                if dep_task_index is None:
                    warn('<dep> pointing to an unknown task')
                deps.append(tasks[dep_task_index])
            
            task.deps = deps
        
        # BUG: (injected) check for if there's not main and return a failure
        if main is None and cls.injected_bug != bug_no_main:
            main = tasks[0]
            warn('There should be a main task')
        
        return cls(tasks, main)
        
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