class Console:
    def __init__(self) -> None:
        self.output = ''
        self.pass_to_print = False

    def print(self):
        self.pass_to_print = True

    def no_print(self):
        self.pass_to_print = False

    def log(self, msg: str) -> None:
        self.output += msg + '\n'
        if self.pass_to_print:
            print(msg)