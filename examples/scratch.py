from isla.solver import ISLaSolver

assign_grammar = {
    '<start>': ['<list>'],
    '<list>': ['<item>', '<item><sep><list>'],
    '<sep>': [', '],
    '<item>': ['<int>'],
    "<int>": ["<leaddigit><digits>"],
    "<digits>": ["", "<digit><digits>"],
    "<digit>": list("0123456789"),
    "<leaddigit>": list("123456789")
} 
a_constraint = """
str.to.int(<list>.<item>) <= str.to.int(<list>.<list>.<item>)
"""

search_tree_grammar = {
    '<start>': ['<tree>'],
    '<tree>': ['<leaf>', 'n(<int>)<tree><tree>'],
    '<leaf>': ['_'],
    "<int>": ["<leaddigit><digits>"],
    "<digits>": ["", "<digit><digits>"],
    "<digit>": list("0123456789"),
    "<leaddigit>": list("123456789")
}

bst= '''
str.to.int(<tree>.<int>) > str.to.int(<tree>.<tree>[1]..<int>)
and
str.to.int(<tree>.<int>) < str.to.int(<tree>.<tree>[2]..<int>)
'''

solver = ISLaSolver(
    grammar=search_tree_grammar,
    formula=bst,
    max_number_free_instantiations=2,  # -f
    max_number_smt_instantiations=2,  # -s
)

for _ in range(30):
    print(solver.solve())
