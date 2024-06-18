from isla.type_defs import Grammar, ParseTree
from isla.derivation_tree import DerivationTree
from isla.language import Formula, parse_bnf, DerivationTree
from isla.fuzzer import GrammarCoverageFuzzer
from isla.language import Formula, ISLaUnparser

from itertools import chain, islice

from islearn.learner import InvariantLearner
from isla.solver import ISLaSolver

from typing import Any, Callable, Iterable
from dataclasses import dataclass

from .condition import Condition

from string_theory.utils import generate_until_absolutely_cannot_anymore


@dataclass(frozen=True)
class ObservableTest:
    test_func: Callable[[str], Any]
    condition: Condition
    learner_options: dict | None = None
    solver_options: dict | None = None

    @property
    def name(self):
        return self.test_func.__name__
    

class ObservableTestSuite:

    def __init__(
        self, 
        grammar: Grammar, 
        formula: Formula | None = None,
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
    
    def debug(self, *message, **kw):
        if self.is_verbose:
            print(str(*message), **kw)
    
    def convert_input(self, tree: DerivationTree):
        return tree.to_string()
    
    def observe(
        self,
        *conditions: Condition,
        learner_options: dict | None = None, 
        solver_options: dict | None = None
    ):
        def decorate(func):
            for condition in conditions:
                self.tests.append(ObservableTest(func, condition, learner_options, solver_options))
            return func;
        
        return decorate

    def learn_preconditions(self, print_progress: bool = True, max_learner_retries: int = 5):
        self.results = []  # reset results

        for test in self.tests:
            if print_progress:
                self.debug(f'\n\nLearning preconditions for {test.name} ({test.condition.description})')
            def validate_condition(input: DerivationTree) -> bool:
                test.condition.reset()
                test.test_func(self.convert_input(input))
                return test.condition.was_triggered

            result = []
            tries = 0
            positive, negative = [], []
            while len(result) == 0 and tries < max_learner_retries:
                np, nn = self.fuzz_samples(validate_condition)
                positive.extend(np)
                negative.extend(nn)
                result: dict[Formula, tuple[float, float]] = InvariantLearner(
                    grammar=self.grammar,
                    prop=validate_condition,
                    positive_examples=positive,
                    negative_examples=negative,
                    **(test.learner_options or {}),
                ).learn_invariants()
                tries += 1

            if tries > 1:
                self.debug(f'tried learning invariants {tries} times.\n')

            self.results.append((test, list(result.keys())))

            if len(result) == 0:
                self.debug('No preconditions found')
            else:
                self.debug("\n".join(map(
                    lambda p: f"{p[1]}: " + ISLaUnparser(p[0]).unparse(),
                    {f: p for f, p in result.items() if p[0] > .0}.items())))

        return self.results

    def preconditions_for(self, test):
        for test, preconditions in self.results:
            if test is test:
                return preconditions
        return None

    def set_catalogue(self, catalogue):
        self.pattern_catalogue = catalogue
        return self

    def fuzz_samples(self, property: Callable[[DerivationTree], bool], num_tries: int = 100):
        self.debug('Fuzzing samples', end='... ')
        solver = ISLaSolver(
            grammar=self.grammar,
            formula=self.formula,
            # enable_optimized_z3_queries=False,
            # max_number_free_instantiations=50,
            # max_number_smt_instantiations=50,
            # max_number_tree_insertion_results=20,
        )

        positive_examples = []
        negative_examples = []

        initial_target = self.target_num_samples // 5

        for _ in range(num_tries):
            if len(positive_examples) > initial_target and len(negative_examples) > initial_target:
                break

            try:
                sample = solver.solve()
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
                self.debug('no positive examples to mutate', end='... ')
                break

            new_positive = []
            new_negative = []

            all_examples = chain(iter(positive_examples), iter(negative_examples))
            for sample in all_examples:
                mutant = solver.mutate(sample)
                if property(mutant):
                    new_positive.append(mutant)
                else:
                    new_negative.append(mutant)

            positive_examples.extend(new_positive)
            negative_examples.extend(new_negative)

        self.debug(f'came up with {len(positive_examples)} positive and {len(negative_examples)} negative')
        # self.debug(f'p example: {positive_examples[len(positive_examples) // 2]}')
        # self.debug(f'n example: {negative_examples[len(negative_examples) // 2]}')
        return positive_examples, negative_examples

    #TODO: allow custom preconditions
    #TODO: setup testing custom preconditions
    #TODO: set up the three-way benchmark

    def results_accuracy(self, num_samples_per_experiment = 1000):
        if len(self.results) == 0:
            raise RuntimeError("No results to evaluate")
        
        raw_inputs = list(islice(self.test_inputs(), num_samples_per_experiment))
        for test, preconditions in self.results:
            for precondition in preconditions:
                assert isinstance(precondition, Formula)
                # measure raw results
                try:
                    constraint_inputs = islice(self.test_inputs(precondition), num_samples_per_experiment)
                    raw_passing, raw_failing = self.split_on_passing(raw_inputs, test)
                    res_passing, res_failing = self.split_on_passing(constraint_inputs, test)
                    yield test, precondition, raw_passing, raw_failing, res_passing, res_failing
                except:
                    yield test, precondition, None, None, None, None

    def test_inputs(self, precondition: Formula | None = None):
        test_constraints = self.formula
        if test_constraints is None:
            test_constraints = precondition
        elif precondition is not None:
            test_constraints = test_constraints & precondition

        solver = None
        if test_constraints is not None:
            solver = ISLaSolver(self.grammar, test_constraints)
        else:
            solver = ISLaSolver(self.grammar)

        return generate_until_absolutely_cannot_anymore(solver)
    
    def split_on_passing(self, samples: Iterable, test: ObservableTest):
        def passes(input: DerivationTree) -> bool:
            test.condition.reset()
            test.test_func(self.convert_input(input))
            return test.condition.was_triggered
        
        passing, failing = [], []
        for sample in samples:
            if passes(sample):
                passing.append(sample)
            else:
                failing.append(sample)
    
        return passing, failing

def learner_results_to_formula(results: dict[Formula, tuple[float, float]]) -> Formula:
    return ...
            
            


