from isla.solver import ISLaSolver
from isla.language import Formula
from isla.type_defs import Grammar
from isla.derivation_tree import DerivationTree

from typing import Callable, Self
from itertools import chain

class InputGenerator:
    def __init__(self, grammar: Grammar, formula: Formula | None, *, debug = lambda i: ...) -> None:
        self.grammar = grammar
        self.formula = formula
        self.debug = debug

    def with_formula(self, formula) -> Self:
        self.formula = formula
        return self
    
    def naive(self, num_samples: int = 1):
        isla_solver = ISLaSolver(grammar=self.grammar, formula=self.formula)
        for _ in range(num_samples):
            yield isla_solver.solve()

    def mutated(self, num_samples: int):
        mutation_ratio = 5
        isla_solver = ISLaSolver(grammar=self.grammar, formula=self.formula)

        generated = []
        for _ in range(num_samples // mutation_ratio):
            sample = isla_solver.solve()
            yield sample
            generated.append(sample)
        
        for _ in range(mutation_ratio - 1):
            mutated = []
            for sample in generated:
                mutant = isla_solver.mutate(sample)
                yield mutant
                mutated.append(mutant)
            generated = mutated
    
    def discriminate_with_mutation(
            self,
            prop: Callable[[DerivationTree], bool],
            target_samples: int = 100,
            num_tries: int = 5,
        ):
        self.debug('Fuzzing samples', end='... ')
        self.solver = ISLaSolver(
            grammar=self.grammar,
            formula=self.formula,
            enable_optimized_z3_queries=False,
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
                self.debug('no positive examples to mutate', end='... ')
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
        
        self.debug(f'came up with {len(positive_examples)} positive and {len(negative_examples)} negative')
        self.debug(f'p example: {positive_examples[len(positive_examples) // 2]}')
        self.debug(f'n example: {negative_examples[len(negative_examples) // 2]}')
        return positive_examples, negative_examples
