import copy
from interpreter.element import Element


class Variable(Element):
    """ Represents variable or a value """

    BOUND_VARIABLE = 'bound'
    FREE_VARIABLE = 'free'

    def __init__(self, var):
        Element.__init__(self)
        self.var = var

    def representation(self):
        return str(self.var)
    
    def __repr__(self) -> str:
        return f"Variable({self.representation()})"

    def detect_variables(self, bound_variables: list = []):
        if type(self.var) is not str:
            return None
        if self.var in bound_variables:
            return list([self.var, self.BOUND_VARIABLE])
        return list([self.var, self.FREE_VARIABLE])

    def applicative_beta_reduction(self) -> bool:
        return False

    def beta_reduction(self) -> bool:
        return False

    def assign_argument(self, name, value):
        if self.is_value():
            return self
        if self.var == name:
            if type(value) == str:
                self.var = value
                return copy.deepcopy(self)
            return copy.deepcopy(value)
        return self

    def is_value(self) -> bool:
        return not type(self.var) == str

    def get_value(self):
        return self.var

    def check_state(self) -> Element:
        return self

    def is_minimal(self):
        return True

    def detect_direct_variables(self):
        if self.is_value():
            return list([])
        return list([self.var])
