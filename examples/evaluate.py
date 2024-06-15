from isla.type_defs import ParseTree
from isla.derivation_tree import DerivationTree

from isla.language import parse_bnf
from isla.solver import ISLaSolver

from string_theory.testing import ObservableTestSuite
from string_theory.condition import Condition
from string_theory.evaluation import evaluate, dump_preconditions
from string_theory.utils import generate_until_absolutely_cannot_anymore

import sys

import simple_config


suite = ObservableTestSuite(grammar=simple_config.grammar, formula=None)#.verbose()

# @simple_suite.observe(c_resolve_conflict)
def test_resolve_conflict(input: str):
    simple_config.parse_config(input)

patterns = {
    "String Length Upper Bound",
    "String Length Lower Bound",
    "String Existence",
    "Existence String Max Length",
    "Existence String Fixed Length",
    "Existence String Max Length",
    "Existence Numeric String Larger Than",
}


@suite.observe(simple_config.value_over_nine, learner_options={'activated_patterns': patterns})
def test_value_over_nine(input: str):
    simple_config.parse_config(input)


@suite.observe(simple_config.c_name, learner_options={'activated_patterns': patterns})
def test_has_name(input: str):
    return "name" in simple_config.parse_config(input)


@suite.observe(~simple_config.c_resolve_conflict, learner_options={'activated_patterns': patterns})
def test_resolved_conflict(input: str):
    return "name" in simple_config.parse_config(input)


constraint = '''
forall <int> container in start:
  exists <digit> elem in container:
    (>= (str.to.int elem) (str.to.int "5"))
'''

def generate():
    generate_until_absolutely_cannot_anymore(ISLaSolver(grammar=simple_config.grammar, formula=None))

def main():
    pass

if __name__ == '__main__':
    command = sys.argv[1]
    match command:
        case 'dump':
            dump_preconditions(suite, './results.dump')
        case 'generate':
            generate()
        case 'evaluate':
            for _ in range(1):
                evaluate(suite, 'data.csv')
        case _:
            print('Unknown command')