from interpreter.element import Element
from interpreter.variable import Variable
import .lambda_element


class Expression(Element):
    """ Represents list of two or more lambda calculus Elements """

    def __init__(self, element_list: list):
        super().__init__()
        self.element_list = element_list

    def representation(self):
        representation = ''
        if len(self.element_list) > 1:
            representation = '('

        for element in self.element_list[:-1]:
            representation += element.representation() + ' '
        if self.element_list[-1]:
            representation += self.element_list[-1].representation()

        if len(self.element_list) > 1:
            representation += ')'
        return representation
    
    def __repr__(self) -> str:
        return f"Expression({self.element_list})"

    def detect_variables(self, bound_variables: list = []):
        result = list()
        for element in self.element_list:
            temp = element.detect_variables(bound_variables)
            if temp:
                if isinstance(element, Variable):
                    result.append(temp)
                else:
                    result += temp
        return result

    def beta_reduction(self) -> bool:
        if len(self.element_list) == 0:
            return False
        if len(self.element_list) == 1:
            if self.element_list[0].beta_reduction():
                return True
            return False

        index = self.get_lambda_index()

        if index == -1:
            index = 0
            while index < len(self.element_list):
                if self.element_list[index].beta_reduction():
                    new_element = self.element_list[index].check_state()
                    if new_element:
                        self.element_list[index] = new_element
                    else:
                        self.element_list.pop(index)
                    return True
                index += 1
            return False

        if (index + 1) < len(self.element_list):
            self.element_list[index] = self.element_list[index].set_argument(self.element_list[index + 1])
            self.element_list.pop(index + 1)
            return True
        return False

    def assign_argument(self, name, value):
        new_element_list = []
        for element in self.element_list:
            temp = element.assign_argument(name, value)
            if temp:
                new_element_list.append(temp)
        if not new_element_list:
            return None
        self.element_list = new_element_list
        if len(self.element_list) == 1:
            return self.element_list[0]
        return self

    def get_lambda_index(self) -> int:
        index = 0
        while index < len(self.element_list):
            if isinstance(self.element_list[index], interpreter.lambda_element.Lambda):
                break
            if isinstance(self.element_list[index], Variable):
                if not self.element_list[index].is_value():
                    return -1
            if isinstance(self.element_list[index], Expression):
                return -1
            index += 1
        if index >= len(self.element_list):
            return -1
        return index

    def applicative_beta_reduction(self) -> bool:
        if self.is_minimal():
            return False
        index = 0
        while index < len(self.element_list):
            if not self.element_list[index].is_minimal():
                self.element_list[index].applicative_beta_reduction()
                self.element_list[index] = self.element_list[index].check_state()
                if not self.element_list[index]:
                    self.element_list.pop(index)
                return True

            index += 1
        return self.beta_reduction()

    def check_state(self) -> Element:
        if len(self.element_list) == 0:
            return None
        if len(self.element_list) == 1:
            return self.element_list[0]
        return self

    def is_minimal(self):
        index = 0
        stopper_expression = False

        while index < len(self.element_list):
            if not self.element_list[index].is_minimal():
                return False
            if isinstance(self.element_list[index], interpreter.lambda_element.Lambda):
                if (index + 1) < len(self.element_list) and not stopper_expression:
                    return False
            if isinstance(self.element_list[index], Expression) or isinstance(self.element_list[index], Variable):
                stopper_expression = True
            index += 1
        return True

    def detect_direct_variables(self):
        var_list = list()
        for element in self.element_list:
            var_list += element.detect_direct_variables()
        return var_list

    def alpha_reduction(self, variables: list=[]):
        for element in self.element_list:
            if isinstance(element, interpreter.lambda_element.Lambda):
                element.alpha_reduction(variables)
