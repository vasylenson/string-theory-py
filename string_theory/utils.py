from isla.type_defs import Grammar
from isla.derivation_tree import DerivationTree
from isla.fuzzer import GrammarCoverageFuzzer
from isla.solver import ISLaSolver

def input_generator(grammar: Grammar):
    fuzzer = GrammarCoverageFuzzer(grammar)
    yield fuzzer.expand_tree(DerivationTree("<start>", None))

def generate_until_absolutely_cannot_anymore(solver: ISLaSolver):
    # print("generate", solver.grammar, solver.formula)
    solver.timeout_seconds = 10
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
            # print('timeout')
            raise StopIteration
    # print('move to mutation')
    while len(generated) > 0:  # till the end of time
        mutants = []
        for sample in generated:
            # print('mutating', sample, end=' - ')
            mutant = solver.mutate(sample, fix_timeout_seconds=10)
            # print('got', mutant)
            mutants.append(mutant)
            yield mutant
        generated = mutants