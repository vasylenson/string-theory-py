from isla.type_defs import Grammar, ParseTree
from isla.derivation_tree import DerivationTree
from isla.language import Formula, parse_bnf, DerivationTree
from isla.fuzzer import GrammarCoverageFuzzer
from isla.language import Formula, ISLaUnparser

from itertools import chain

from islearn.learner import InvariantLearner
from isla.solver import ISLaSolver

from typing import Any, Callable, Self
from dataclasses import dataclass


class Condition:
    def __init__(self, description: str | int) -> None:
        self.description = description
        self._triggered_count = 0
    
    def trigger(self):
        self._triggered_count += 1
    
    def reset(self):
        self._triggered_count = 0
    
    def describe(self, description) -> Self:
        '''Update the condition's description'''
        self.description = description
        return self

    @property
    def was_triggered(self):
        return self._triggered_count > 0
    
    @property
    def count(self):
        return self._triggered_count
    
    def __and__(self, other):
        return ConjunctiveCondition(self, other)

    def __or__(self, other):
        return DisjunctiveCondition(self, other)
    
    def __invert__(self):
        return NegatedCondition(self)


class NegatedCondition(Condition):
    def __init__(self, condition: Condition) -> None:
        self.condition = condition
        self.description = f'Not ({condition.description})'

    def reset(self):
        return self.condition.reset()
    
    @property
    def was_triggered(self):
        return not self.condition.was_triggered
    
    @property
    def count(self):
        return int(self.was_triggered)

    def trigger(self):
        raise Exception('Negation conditions cannot be triggered')

class ConjunctiveCondition(Condition):
    def __init__(self, *conditions: Condition):
        self.sub_conditions = conditions
    
    def trigger(self):
        raise Exception('Combination conditions cannot be triggered')
    
    def reset(self):
        for cond in self.sub_conditions:
            cond.reset()

    @property
    def was_triggered(self) -> bool:
        return all(c.was_triggered for c in self.sub_conditions)
    
    @property
    def count(self) -> int:
        return int(self.was_triggered)
    
    @property
    def description(self) -> str:
        return ' and '.join(c.description for c in self.sub_conditions)


class DisjunctiveCondition(ConjunctiveCondition):
    @property
    def was_triggered(self):
        return any(c.was_triggered for c in self.sub_conditions)
    
    @property
    def description(self) -> str:
        return ' or '.join(c.description for c in self.sub_conditions)


@dataclass
class ObservableTest:
    test_func: Callable[[str], Any]
    condition: Condition
    learner_options: dict | None = None
    solver_options: dict | None = None
    

class ObservableTestSuite:

    def __init__(
        self, 
        grammar: Grammar, 
        formula: Formula, 
        input_adapter: Callable[[DerivationTree], Any] | None = None,
        target_num_samples: int = 200,
    ) -> None:
        self.tests: list[ObservableTest] = []
        self.grammar = grammar
        self.formula = formula
        self.target_num_samples = target_num_samples

        self.results = []
        self.is_verbose = False
    
        if input_adapter:
            self.convert_input = input_adapter
    
    def verbose(self):
        self.is_verbose = True
        return self
    
    def silent(self):
        self.is_verbose = False
        return self
    
    def convert_input(self, tree: DerivationTree):
        return tree.to_string()
    
    def observe(self, condition: Condition, learner_options = None, solver_options = None):
        def decorate(func):
            self.tests.append(ObservableTest(func, condition, learner_options, solver_options))
            return func;
        
        return decorate

    def learn_preconditions(self, print_progress: bool = True, max_learner_retries: int = 5):
        for test in self.tests:
            if print_progress:
                print(f'\n\nLearning preconditions for {test.condition.description}')
            def validate_condition(input: DerivationTree) -> bool:
                test.condition.reset()
                test.test_func(self.convert_input(input))
                return test.condition.was_triggered
            
            result = []
            tries = 0
            while len(result) == 0 and tries < max_learner_retries:
                positive, negative = self.fuzz_samples(validate_condition)
                result: dict[Formula, tuple[float, float]] = InvariantLearner(
                    grammar=self.grammar,
                    prop=validate_condition,
                    positive_examples=positive,
                    negative_examples=negative,
                    **(test.learner_options or {}),
                ).learn_invariants()
                tries += 1
            
            if tries > 1:
                print(f'tried learning invariants {tries} times.\n')

            self.results.append((test, result))

            if print_progress: 
                if len(result) == 0:
                    print('No preconditions found')
                    continue
    
                print("\n".join(map(
                    lambda p: f"{p[1]}: " + ISLaUnparser(p[0]).unparse(),
                    {f: p for f, p in result.items() if p[0] > .0}.items())))

    def fuzz_samples(self, property: Callable[[DerivationTree], bool], num_tries: int = 100):
        print('Fuzzing samples', end='... ')
        self.solver = ISLaSolver(
            grammar=self.grammar,
            formula=self.formula,
            enable_optimized_z3_queries=False,
            max_number_free_instantiations=50,
            max_number_smt_instantiations=50,
            max_number_tree_insertion_results=20,
        )

        positive_examples = []
        negative_examples = []

        initial_target = self.target_num_samples // 5

        for _ in range(num_tries):
            if len(positive_examples) > initial_target and len(negative_examples) > initial_target:
                break
            
            try:
                sample = self.solver.solve()
                if property(sample):
                    positive_examples.append(sample)
                else:
                    negative_examples.append(sample)
            except StopIteration:
                break

        # print(f'so far p {len(positive_examples)} n {len(negative_examples)}')
        # print('mutating')
        tried = 0
        while len(positive_examples) < self.target_num_samples and tried < num_tries:
            if len(positive_examples) == 0:
                print('no positive examples to mutate', end='... ')
                break

            new_positive = []
            new_negative = []

            all_examples = chain(iter(positive_examples), iter(negative_examples))
            for sample in all_examples:
                mutant = self.solver.mutate(sample)
                if property(mutant):
                    new_positive.append(mutant)
                else:
                    new_negative.append(mutant)

            positive_examples.extend(new_positive)
            negative_examples.extend(new_negative)
        
        print(f'came up with {len(positive_examples)} positive and {len(negative_examples)} negative')
        print(f'p example: {positive_examples[len(positive_examples) // 2]}')
        print(f'n example: {negative_examples[len(negative_examples) // 2]}')
        return positive_examples, negative_examples
            


