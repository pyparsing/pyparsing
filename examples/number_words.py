# number_words.py
#
# Copyright 2020, Paul McGuire
#
# Parser/evaluator for expressions of numbers as written out in words:
#  - one
#  - seven
#  - twelve
#  - twenty six
#  - forty-two
#  - one hundred and seven
#
#
#  BNF:
"""
    optional_and ::= ["and" | "-"]
    optional_dash ::= ["-"]
    units ::= one | two | three | ... | nine
    teens_only ::= eleven | twelve | ... | nineteen
    teens ::= ten | teens_only
    tens ::= twenty | thirty | ... | ninety
    hundreds ::= (units | teens_only | tens optional_dash units) "hundred"
    one_to_99 ::= units | teens | (tens [optional_dash units])
    thousands = one_to_99 "thousand"

    number = [thousands] [hundreds] optional_and units | [thousands] optional_and hundreds | thousands
"""
import pyparsing as pp
from operator import mul
import pyparsing.diagram


def define_numeric_word(s, value):
    return pp.CaselessKeyword(s).addParseAction(lambda: value)


def define_numeric_word_range(s, vals):
    if isinstance(s, str):
        s = s.split()
    return pp.MatchFirst(
        define_numeric_word(nm, nm_value) for nm, nm_value in zip(s, vals)
    )


opt_dash = pp.Optional(pp.Suppress("-")).setName("optional '-'")
opt_and = pp.Optional((pp.CaselessKeyword("and") | "-").suppress()).setName(
    "optional 'and'"
)

zero = define_numeric_word_range("zero oh", [0, 0])
one_to_9 = define_numeric_word_range(
    "one two three four five six seven eight nine", range(1, 9 + 1)
).setName("1-9")
eleven_to_19 = define_numeric_word_range(
    "eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen",
    range(11, 19 + 1),
).setName("eleven_to_19")
ten_to_19 = (define_numeric_word("ten", 10) | eleven_to_19).setName("ten_to_19")
one_to_19 = (one_to_9 | ten_to_19).setName("1-19")
tens = define_numeric_word_range(
    "twenty thirty forty fifty sixty seventy eighty ninety", range(20, 90 + 1, 10)
)
hundreds = (
    one_to_9 | eleven_to_19 | (tens + opt_dash + one_to_9)
) + define_numeric_word("hundred", 100)
one_to_99 = (
    one_to_19 | (tens + pp.Optional(opt_dash + one_to_9)).addParseAction(sum)
).setName("1-99")
one_to_999 = (
    (pp.Optional(hundreds + opt_and) + one_to_99 | hundreds).addParseAction(sum)
).setName("1-999")
thousands = one_to_999 + define_numeric_word("thousand", 1000)
hundreds.setName("100s")
thousands.setName("1000s")


def multiply(t):
    return mul(*t)


hundreds.addParseAction(multiply)
thousands.addParseAction(multiply)

numeric_expression = (
    pp.Optional(thousands + opt_and) + pp.Optional(hundreds + opt_and) + one_to_99
    | pp.Optional(thousands + opt_and) + hundreds
    | thousands
).setName("numeric_words")
numeric_expression.addParseAction(sum)


if __name__ == "__main__":
    numeric_expression.runTests(
        """
        one
        seven
        twelve
        twenty six
        forty-two
        two hundred
        twelve hundred
        one hundred and eleven
        ninety nine thousand nine hundred and ninety nine
        nine hundred thousand nine hundred and ninety nine
        nine hundred and ninety nine thousand nine hundred and ninety nine
        nineteen hundred thousand nineteen hundred and ninety nine
        """
    )

    # create railroad diagram
    numeric_expression.create_diagram("numeric_words_diagram.html", vertical=5)
