#
# simpleArith.py
#
# Example of defining an arithmetic expression parser using
# the infix_notation helper method in pyparsing.
#
# Copyright 2006, by Paul McGuire
#
import sys
from pyparsing import *

ppc = pyparsing_common

ParserElement.enable_packrat()
sys.setrecursionlimit(3000)

integer = ppc.integer
variable = Word(alphas, exact=1)
operand = integer | variable

expop = Literal("^")
signop = one_of("+ -")
multop = one_of("* /")
plusop = one_of("+ -")
factop = Literal("!")

# To use the infix_notation helper:
#   1.  Define the "atom" operand term of the grammar.
#       For this simple grammar, the smallest operand is either
#       an integer or a variable.  This will be the first argument
#       to the infix_notation method.
#   2.  Define a list of tuples for each level of operator
#       precedence.  Each tuple is of the form
#       (opExpr, numTerms, rightLeftAssoc, parseAction), where
#       - opExpr is the pyparsing expression for the operator;
#          may also be a string, which will be converted to a Literal
#       - numTerms is the number of terms for this operator (must
#          be 1 or 2)
#       - rightLeftAssoc is the indicator whether the operator is
#          right or left associative, using the pyparsing-defined
#          constants OpAssoc.RIGHT and OpAssoc.LEFT.
#       - parseAction is the parse action to be associated with
#          expressions matching this operator expression (the
#          parse action tuple member may be omitted)
#   3.  Call infix_notation passing the operand expression and
#       the operator precedence list, and save the returned value
#       as the generated pyparsing expression.  You can then use
#       this expression to parse input strings, or incorporate it
#       into a larger, more complex grammar.
#
expr = infix_notation(
    operand,
    [
        (factop, 1, OpAssoc.LEFT),
        (expop, 2, OpAssoc.RIGHT),
        (signop, 1, OpAssoc.RIGHT),
        (multop, 2, OpAssoc.LEFT),
        (plusop, 2, OpAssoc.LEFT),
    ],
)

test = [
    "9 + 2 + 3",
    "9 + 2 * 3",
    "(9 + 2) * 3",
    "(9 + -2) * 3",
    "(9 + -2) * 3^2^2",
    "(9! + -2) * 3^2^2",
    "M*X + B",
    "M*(X + B)",
    "1+2*-3^4*5+-+-6",
    "(a + b)",
    "((a + b))",
    "(((a + b)))",
    "((((a + b))))",
    "((((((((((((((a + b))))))))))))))",
]
for t in test:
    print(t)
    print(expr.parse_string(t))
    print("")
