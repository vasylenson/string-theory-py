
class Element:
    """ Base class representing every element in lambda calculus """

    def __init__(self):
        pass

    def normal_evaluation(self):
        """ Evaluates expression from left, starting from outside using beta reduction """
        while self.beta_reduction():
            pass

    def applicative_evaluation(self):
        while self.applicative_beta_reduction():
            pass

    def representation(self) -> str:
        """ Returns string of element representation """
        pass

    def detect_variables(self, bound_variables: list = []) -> list:
        """ Returns list of all variables with its type,
        in as form: [variable name, variable type] """
        pass

    def is_minimal(self):
        """ Returns true if the expression is in minimal form: there is no more beta_reduction possible """
        pass

    def beta_reduction(self) -> bool:
        """ Application of expression: takes first available value
        and replaces all the occurrences of given variable with the value
        Every class derivation has its own implementation """
        pass

    def applicative_beta_reduction(self) -> bool:
        pass

    def check_state(self):
        """ Checks current state of element and returns itself or simplified version of itself,
        without changing any aspect of itself except for internal implementation a brackets of representation """
        pass

    def detect_direct_variables(self):
        """ Detects free variables in qa given scope """
        pass

    def alpha_reduction(self, variables: list=[]):
        """ Renames variables when match conflict is detected during beta reduction """
        pass

