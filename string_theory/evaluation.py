from string_theory.testing import ObservableTestSuite, ObservableTest
from string_theory.generator import InputGenerator

from isla.language import Formula, ISLaUnparser

from dataclasses import dataclass
from csv import writer, QUOTE_STRINGS


type PrecAndSampleSize = tuple[float, int]


@dataclass(frozen=True)
class EvaluationResult():
    test: ObservableTest
    # only_grammar_perf: PrecAndSampleSize
    grammar_spec_perf: PrecAndSampleSize

    learned_perf: PrecAndSampleSize
    learned_formula: list[Formula]

    # learned_custom_perf: PrecAndSampleSize
    # learned_custom_formula: list[Formula]

    def __str__(self) -> str:
        text = f'[Test {self.test.name()}]\n'
        text = f'Observed condition: {self.test.condition.description}\n\n'

        text += 'Precision of test input fuzzing:\n'
        # text += f'- only grammar: {format_pss(self.grammar_perf)}\n'
        text += f'- grammar and general input constraints: {format_pss(self.grammar_spec_perf)}\n'
        text += f'- with learned preconditions: {format_pss(self.learned_perf)}\n'
        # text += f'- with learned preconditions (custom catalogue): {format_pss(self.learned_custom_formula)}\n\n'

        text += f'Preconditions learned: \n'
        # text += format_formulas(self.learned_formula)

        # text += f'\n\nPreconditions learned (with the custom catalogue): \n'
        # text += format_formulas(self.learned_formula)


def format_pss(data: PrecAndSampleSize) -> str:
    precision, sample_size = data
    return f'{precision}% ({sample_size} sample)'


def evaluate(suite: ObservableTestSuite, output_file: str):
    file = open(output_file, 'a+', newline='')
    result_log = writer(file, quoting=QUOTE_STRINGS)

    print('Learning preconditions')
    suite.learn_preconditions()

    print('Evaluating preconditions')
    current_test = None
    measured = 0
    timed_out = 0
    result_log.writerow(['Test name', 'Precondition', 'Raw accuracy', 'Resulting accuracy', 'Measured'])
    for test, precondition, raw_p, raw_n, res_p, res_n in suite.results_accuracy(100):
        if test is not current_test:
            current_test = test
            print(f'\n[Test] {test.name} ({test.condition.description})')
        precondition_code = ISLaUnparser(precondition).unparse()

        if (raw_p is None):
            result_log.writerow([test.name, precondition_code, 0, 0, False])
            # print("Couldn't generate enough solutions to evaluate, likely due to a timeout.\n")
            timed_out += 1
            continue

        measured += 1

        raw_acc = len(raw_p) / (len(raw_p) + len(raw_n)) * 100
        res_acc = len(res_p) / (len(res_p) + len(res_n)) * 100
        print(f'- Found precondition (accuracy {raw_acc}% -> {res_acc}%)')
        print(precondition_code)
        result_log.writerow([test.name, precondition_code, raw_acc, res_acc, True])
    
    file.close()
    print('Measured', measured, 'and timed out', timed_out, 'preconditions')


def dump_preconditions(suite: ObservableTestSuite, path):
    results = suite.learn_preconditions()
    dump = []
    for test, results in results:
        entry = f'[{test.name}]'
        for formula in results:
            entry += '\n\n' + ISLaUnparser(formula).unparse()
        dump.append(entry)

    with open(path, 'w') as f:
        f.write('\n\n\n'.join(dump))

