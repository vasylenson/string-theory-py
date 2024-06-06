'''
Applicative parser for the lambda expression language recovered from examples
'''

from types import UnionType
from typing import Any, TypeVar, Callable, Self

from .variable import Variable
from .expression import Expression

TResult = TypeVar('TResult')
TMapped = TypeVar('TMapped')

type ParserFunc[TResult] = Callable[[str], tuple[TResult | None, str]]

class Parser:

    def __init__(self, parse_func: ParserFunc[TResult]) -> None:
        self.parse = parse_func

    def parse(self, input: str) -> tuple[TResult, str]:
        pass

    def map(self, mapper: Callable[[TResult], TMapped]) -> Self:
        '''Implement Functor for Parser'''
        def mapped_parse(input: str) -> tuple[TResult, str]:
            result, rest = self.parse(input)

            if result is None:
                return None, input

            return mapper(result), rest
        
        return Parser(mapped_parse)
    
    def apply(self, argument_parser: Self) -> Self:
        '''
        Implements applicative combination:
        ```
            self <*> argument parser
        ```
        '''
        def applied_parse(input: str) -> tuple[TResult, str]:
            partial_parser_output: tuple[Callable[[TResult], TMapped], str] = self.parse(input)
            partial_result, partial_rest = partial_parser_output

            own_result, own_rest = argument_parser.parse(partial_rest)
            return partial_result(own_result), own_rest
        
        return Parser(applied_parse)
    
    def __gt__(self, other: Self) -> Self:
        return self.chain(self, other).map(lambda list: list[1])
    
    def __lt__(self, other: Self) -> Self:
        return self.chain(self, other).map(lambda list: list[0])
    
    @staticmethod
    def pure(value: TResult) -> Self:
        '''Implement Applicative.pure for Parser'''
        return Parser(lambda input: (value, input))
    
    @staticmethod
    def string(string: str) -> Self:
        '''Parse a particular string or fail (parse `None`)'''
        def parse_string(input: str) -> tuple[str | None, str]:
            if input.startswith(string):
                return string, input[len(string):]
            
            return None, input
        
        return Parser(parse_string)
    
    @staticmethod
    def predicate(predicate: Callable[[str], bool]) -> Self:
        def parse_predicate(input: str) -> tuple[str | None, str]:
            parsed = []

            for ch in input:
                if not predicate(ch):
                    break

                parsed.append(ch)

            return (
                (None, input)
                if len(parsed) == 0 
                else (''.join(parsed), input[len(parsed):])
            )
        
        return Parser(parse_predicate)
    
    @staticmethod
    def chain(*parsers: Self) -> Self:
        assert len(parsers) > 0

        def parse_chain(input: str) -> tuple[list | None, str]:
            remaining_input = input
            results = []

            for parser in parsers:
                result, rest = parser.parse(remaining_input)

                if result is None:
                    return None, input  # fail the entire chain
                
                results.append(result)
                remaining_input = rest
            
            return results, remaining_input
        
        return Parser(parse_chain)
    
    @staticmethod
    def some(parser: Self) -> Self:
        def parse_some(input: str) -> tuple[list | None, str]:
            remaining_input = input
            results = []

            while len(remaining_input) > 0:
                result, rest = parser.parse(remaining_input)

                if result is None:
                    break
                
                results.append(result)
                remaining_input = rest
            
            if len(results) == 0:
                return None, input
            
            return results, remaining_input
        
        return Parser(parse_some)
    
    @classmethod
    def any(cls, parser: Self) -> Self:
        return cls.one_of(lambda: cls.some(parser), lambda: cls.pure([]))
    
    @classmethod
    def sep(cls, item_parser: Self, separator: str) -> Self:
        sep_items = cls.any(cls.string(separator) > item_parser)
        return cls.chain(item_parser, sep_items).map(lambda results: [results[0]] + results[1])
    
    @classmethod
    def ws(cls) -> Self:
        return cls.some(Parser.string(' '))

    @staticmethod
    def one_of(*lazy_parsers: Callable[[], Self]):
        def parse_one_of(input: str) -> Self:
            for lazy_parser in lazy_parsers:
                result, rest = lazy_parser().parse(input)
                if result is not None:
                    return result, rest
            return None, input
        
        return Parser(parse_one_of)

def parens(parser: Parser) -> Parser:
    return (Parser.string('(') > parser) < Parser.string(')')

parse_int = Parser.predicate(str.isnumeric).map(int)

# language parser

def expression():
    return Parser.one_of(lambda_expr, application, var_name)

def lambda_expr():
    return parens(Parser.chain(
        Parser.string('lambda '),
        Parser.some(var_name),
        Parser.string('. '),
        expression(),
    ))

def application():
    return parens(Parser.sep(var_name, ' ')).map(Expression)

def var_name():
    return Parser(parse_var_name).map(Variable)

def parse_var_name(input: str) -> tuple[str | None, str]:
    if not input[0].isalpha():
        return None, input
    
    rest = input[1:].lstrip("'")

    return input[:-len(rest)], rest
