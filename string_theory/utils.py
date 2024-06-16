from isla.type_defs import Grammar
from isla.derivation_tree import DerivationTree
from isla.fuzzer import GrammarCoverageFuzzer
from isla.solver import ISLaSolver

from isla.language import parse_bnf, parse_isla, Formula

from multiprocessing import Process, Queue
from typing import Generator, Any
from itertools import islice

def input_generator(grammar: Grammar):
    fuzzer = GrammarCoverageFuzzer(grammar)
    yield fuzzer.expand_tree(DerivationTree("<start>", None))

def generate_until_absolutely_cannot_anymore(solver: ISLaSolver, timeouts: int = 10):
    # print("generate", solver.grammar, solver.formula)
    solver.timeout_seconds = timeouts
    generated = []
    keep_going = True
    while keep_going:
        try:
            solution = solver.solve()
            generated.append(solution)
            # print('solution', solution)
            yield solution
        except StopIteration:
            keep_going = False
        except TimeoutError as e:
            # solver = ISLaSolver(solver.grammar, solver.formula)
            keep_going = False
    # print('move to mutation')
    while len(generated) > 0:  # till the end of time
        mutants = []
        for sample in generated:
            # print('mutating', sample, end=' - ')
            mutant = solver.mutate(sample)
            # print('got', mutant)
            mutants.append(mutant)
            yield mutant
        generated = mutants

def generate_with_retries(solver: ISLaSolver, timeout_sec: int = 20) -> Generator[DerivationTree, Any, None]:
    keep_going = True
    while keep_going:
        generator = generate_until_absolutely_cannot_anymore(solver)
        for solution in islice(generator, 30):
            yield solution
        
        print('\n\n\nnew generator\n\n\n')
        solver = ISLaSolver(solver.grammar, solver.formula)

def read_bnf(filename):
    with open(filename, 'r') as f:
        return parse_bnf(f.read())

def read_isla(filename, grammar: Grammar):
    with open(filename, 'r') as f:
        return parse_isla(f.read(), grammar)