from isla.type_defs import Grammar
from isla.derivation_tree import DerivationTree
from isla.fuzzer import GrammarCoverageFuzzer

def input_generator(grammar: Grammar):
    fuzzer = GrammarCoverageFuzzer(grammar)
    yield fuzzer.expand_tree(DerivationTree("<start>", None))