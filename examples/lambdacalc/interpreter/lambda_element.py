from interpreter.element import Element


class Lambda(Element):
    """ Represents lambda function, which includes list of arguments and body,
    which must also be an instance of Element"""

    def __init__(self, arguments: list, body):
        Element.__init__(self)
        self.arguments = arguments
        self.body = body

    def representation(self) -> str:
        representation = '(lambda '
        for argument in self.arguments:
            representation += argument
        representation += '. ' + self.body.representation()
        return representation + ')'

    def detect_variables(self, bound_variables: list = []):
        bound_variables = self.arguments + bound_variables
        return self.body.detect_variables(bound_variables)

    def applicative_beta_reduction(self) -> bool:
        return self.body.applicative_beta_reduction()

    def beta_reduction(self) -> bool:
        if self.body.beta_reduction():
            return True
        return False

    def set_argument(self, value):
        self.alpha_reduction_on_argument(value)
        name = self.arguments[0]
        self.arguments.pop(0)
        self.body = self.body.assign_argument(name, value)
        if not self.arguments:
            return self.body
        return self

    def assign_argument(self, name, value):
        if name in self.arguments:
            return self
        self.body.assign_argument(name, value)
        return self

    def check_state(self) -> Element:
        if len(self.arguments) == 0:
            return self.body.check_state()
        return self

    def is_minimal(self):
        return self.body.is_minimal()

    def detect_direct_variables(self):
        return list()

    def alpha_reduction_on_argument(self, argument: Element):
        variables = argument.detect_direct_variables()
        self.alpha_reduction(variables)

    def alpha_reduction(self, variables: list=[]):
        index = 0
        while index < len(self.arguments):
            if self.arguments[index] in variables:
                new_name = str(self.arguments[index]) + "'"
                self.body.assign_argument(self.arguments[index], new_name)
                self.arguments[index] = new_name
            index += 1
        self.body.alpha_reduction(variables)


