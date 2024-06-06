from isla.solver import ISLaSolver

class Generator:
    def __init__(self, isla_solver: ISLaSolver | None = None, *, grammar, formula) -> None:
        if not isla_solver and not (grammar and formula):
            raise ValueError("Generator requires either an ISLaSolver or a combination of a grammar and a formula")

        self.isla_solver = isla_solver or ISLaSolver(grammar=grammar, formula=formula)
    
    def generate(self, num_samples: int = 1):
        for _ in range(num_samples):
            yield self.isla_solver.solve()
    
    @property
    def grammar(self):
        return self.isla_solver.grammar