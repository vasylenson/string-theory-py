import string
from isla.helpers import srange

from isla.solver import ISLaSolver

SCRIPTSIZE_C_GRAMMAR = {
    "<start>": ["<statement>"],
    "<statement>": [
        "<block>",
        "if<paren_expr> <statement> else <statement>",
        "if<paren_expr> <statement>",
        "while<paren_expr> <statement>",
        "do <statement> while<paren_expr>;",
        "<expr>;",
        ";",
    ],
    "<block>": ["{<statements>}"],
    "<statements>": ["<block_statement><statements>", ""],
    "<block_statement>": ["<statement>", "<declaration>"],
    "<declaration>": ["int <id> = <expr>;", "int <id>;"],
    "<paren_expr>": ["(<expr>)"],
    "<expr>": [
        "<id> = <expr>",
        "<test>",
    ],
    "<test>": [
        "<sum> < <sum>",
        "<sum>",
    ],
    "<sum>": [
        "<sum> + <term>",
        "<sum> - <term>",
        "<term>",
    ],
    "<term>": [
        "<paren_expr>",
        "<id>",
        "<int>",
    ],
    "<id>": srange(string.ascii_lowercase),
    "<int>": [
        "<digit_nonzero><digits>",
        "<digit>",
    ],
    "<digits>": [
        "<digit><digits>",
        "<digit>",
    ],
    "<digit>": srange(string.digits),
    "<digit_nonzero>": list(set(srange(string.digits)) - {"0"}),
}

# Forall <id>s use_id in any expression (i.e., only RHSs),
#   there must be a <declaration> decl,
#     which occurs before use_id and on the same or a higher <block> level,
#       that assigns use_id a value.
SCRIPTSIZE_C_DEF_USE_CONSTR_TEXT = """
forall <expr> expr in start:
  forall <id> use_id in expr:
    exists <declaration> decl="int {<id> def_id}[ = <expr>];" in start:
      (level("GE", "<block>", decl, expr) and 
      (before(decl, expr) and 
      (= use_id def_id)))

and

forall <declaration> declaration="int {<id> def_id}[ = <expr>];" in start:
   forall <declaration> other_declaration="int {<id> other_def_id}[ = <expr>];" in start:
     (same_position(declaration, other_declaration) xor not (= def_id other_def_id))
"""

solver = ISLaSolver(
    grammar=SCRIPTSIZE_C_GRAMMAR,
    formula=SCRIPTSIZE_C_DEF_USE_CONSTR_TEXT,
)

sample = "{int h;h;}"

def solve():
    print('solving')
    for i in range(500):
        print(solver.solve())

def check():
    print("checking", sample)
    print(solver.check(sample))

if __name__ == '__main__':
    check()