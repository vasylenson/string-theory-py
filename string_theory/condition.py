from typing import Self

class Condition:
    def __init__(self, description: str | int) -> None:
        self.description = description
        self._triggered_count = 0
    
    def trigger(self):
        self._triggered_count += 1
    
    def reset(self):
        self._triggered_count = 0
    
    def describe(self, description) -> Self:
        '''Update the condition's description'''
        self.description = description
        return self

    @property
    def was_triggered(self):
        return self._triggered_count > 0
    
    @property
    def count(self):
        return self._triggered_count
    
    def __and__(self, other):
        return ConjunctiveCondition(self, other)

    def __or__(self, other):
        return DisjunctiveCondition(self, other)
    
    def __invert__(self):
        return NegatedCondition(self)


class NegatedCondition(Condition):
    def __init__(self, condition: Condition) -> None:
        self.condition = condition
        self.description = f'Not ({condition.description})'

    def reset(self):
        return self.condition.reset()
    
    @property
    def was_triggered(self):
        return not self.condition.was_triggered
    
    @property
    def count(self):
        return int(self.was_triggered)

    def trigger(self):
        raise Exception('Negation conditions cannot be triggered')

class ConjunctiveCondition(Condition):
    def __init__(self, *conditions: Condition):
        self.sub_conditions = conditions
    
    def trigger(self):
        raise Exception('Combination conditions cannot be triggered')
    
    def reset(self):
        for cond in self.sub_conditions:
            cond.reset()

    @property
    def was_triggered(self) -> bool:
        return all(c.was_triggered for c in self.sub_conditions)
    
    @property
    def count(self) -> int:
        return int(self.was_triggered)
    
    @property
    def description(self) -> str:
        return ' and '.join(c.description for c in self.sub_conditions)


class DisjunctiveCondition(ConjunctiveCondition):
    @property
    def was_triggered(self):
        return any(c.was_triggered for c in self.sub_conditions)
    
    @property
    def description(self) -> str:
        return ' or '.join(c.description for c in self.sub_conditions)
