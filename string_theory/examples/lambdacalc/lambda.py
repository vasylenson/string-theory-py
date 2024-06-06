from isla.solver import ISLaSolver
import sys

def read_file(path: str) -> str:
    with open(path, 'r') as file:
        return file.read()

solver = ISLaSolver(
    grammar=read_file('examples/lambda/lambda.bnf'),
    formula=read_file('examples/lambda/lambda.isla'),
)

samples = map(read_file, ['examples/lambda/samples/1.lambda'])

def solve():
    for _ in range(100):
        print(solver.solve())

def check():
    for sample in samples:
        print(sample)
        print(solver.check(sample))

if __name__ == '__main__':
    solve()
