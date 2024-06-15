from interpreter.element import Element
from interpreter.variable import Variable


class Operator(Element):

    operator_list = {'*': 'multiply', '-': 'subtract', '+': 'addition', '/': 'divide'}

    def __init__(self, operator_type, expression_0: Element, expression_1: Element):
        super().__init__()
        self.operator_type = operator_type
        self.expression_0 = expression_0
        self.expression_1 = expression_1

    def representation(self) -> str:
        return '( ' + self.operator_type + ' ' + self.expression_0.representation() + ' ' + self.expression_1.representation() + ')'

    def detect_variables(self, bound_variables: list = []) -> list:
        bound_variables_0 = self.expression_0.detect_variables(bound_variables)
        bound_variables_1 = self.expression_1.detect_variables(bound_variables)
        return bound_variables_0 + bound_variables_1

    def is_minimal(self):
        if self.expression_0.is_minimal():
            if self.expression_1.is_minimal():
                if self.is_evaluable():
                    return False
                return True
        return False

    def beta_reduction(self) -> bool:
        if self.expression_0.beta_reduction():
            self.expression_0 = self.expression_0.check_state()
            return True
        if self.expression_1.beta_reduction():
            self.expression_1 = self.expression_1.check_state()
            return True
        if self.is_evaluable():
            return True
        return False

    def applicative_beta_reduction(self) -> bool:
        if self.expression_0.applicative_beta_reduction():
            self.expression_0 = self.expression_0.check_state()
            return True
        if self.expression_1.applicative_beta_reduction():
            self.expression_1 = self.expression_1.check_state()
            return True
        if self.is_evaluable():
            return True
        return False

    def check_state(self) -> Element:
        if self.is_evaluable():
            return Variable(self.expression_0.get_value() * self.expression_1.get_value())
        return self

    def is_evaluable(self):
        if isinstance(self.expression_0, Variable) and isinstance(self.expression_1, Variable) \
                and self.expression_0.is_value() and self.expression_1.is_value():
            return True
        return False

    def assign_argument(self, name, value):
        self.expression_0 = self.expression_0.assign_argument(name, value)
        self.expression_1 = self.expression_1.assign_argument(name, value)
        if self.is_evaluable():
            operator_function = self.operator_list[self.operator_type]
            method = getattr(self, operator_function)
            return Variable(method(self.expression_0.get_value(), self.expression_1.get_value()))
        return self

    @staticmethod
    def multiply(x, y):
        return x * y

    @staticmethod
    def subtract(x, y):
        return x - y

    @staticmethod
    def addition(x, y):
        return x + y

    @staticmethod
    def divide(x, y):
        return x + y
