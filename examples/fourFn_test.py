# fourFn.py
#
# Demonstration of the pyparsing module, implementing a simple 4-function expression parser,
# with support for scientific notation, and symbols for e and pi.
# Extended to add exponentiation and simple built-in functions.
# Extended test cases, simplified pushFirst method.
# Removed unnecessary expr.suppress() call (thanks Nathaniel Peterson!), and added Group
# Changed fnumber to use a Regex, which is now the preferred method
# Reformatted to latest pypyparsing features, support multiple and variable args to functions
#
# Copyright 2003-2019 by Paul McGuire
#
import math

from pyparsing import ParseException

from examples.fourFn import exprStack, BNF, evaluate_stack


def test(s, expected):
    exprStack[:] = []
    try:
        results = BNF().parseString(s, parseAll=True)
        val = evaluate_stack(exprStack[:])
    except ParseException as pe:
        print(s, "failed parse:", str(pe))
    except Exception as e:
        print(s, "failed eval:", str(e), exprStack)
    else:
        if val == expected:
            print(s, "=", val, results, "=>", exprStack)
        else:
            print(s + "!!!", val, "!=", expected, results, "=>", exprStack)


test("9", 9)
test("-9", -9)
test("--9", 9)
test("-E", -math.e)
test("9 + 3 + 6", 9 + 3 + 6)
test("9 + 3 / 11", 9 + 3.0 / 11)
test("(9 + 3)", (9 + 3))
test("(9+3) / 11", (9 + 3.0) / 11)
test("9 - 12 - 6", 9 - 12 - 6)
test("9 - (12 - 6)", 9 - (12 - 6))
test("2*3.14159", 2 * 3.14159)
test("3.1415926535*3.1415926535 / 10", 3.1415926535 * 3.1415926535 / 10)
test("PI * PI / 10", math.pi * math.pi / 10)
test("PI*PI/10", math.pi * math.pi / 10)
test("PI^2", math.pi ** 2)
test("round(PI^2)", round(math.pi ** 2))
test("6.02E23 * 8.048", 6.02e23 * 8.048)
test("e / 3", math.e / 3)
test("sin(PI/2)", math.sin(math.pi / 2))
test("10+sin(PI/4)^2", 10 + math.sin(math.pi / 4) ** 2)
test("trunc(E)", int(math.e))
test("trunc(-E)", int(-math.e))
test("round(E)", round(math.e))
test("round(-E)", round(-math.e))
test("E^PI", math.e ** math.pi)
test("exp(0)", 1)
test("exp(1)", math.e)
test("2^3^2", 2 ** 3 ** 2)
test("(2^3)^2", (2 ** 3) ** 2)
test("2^3+2", 2 ** 3 + 2)
test("2^3+5", 2 ** 3 + 5)
test("2^9", 2 ** 9)
test("sgn(-2)", -1)
test("sgn(0)", 0)
test("sgn(0.1)", 1)
test("foo(0.1)", None)
test("round(E, 3)", round(math.e, 3))
test("round(PI^2, 3)", round(math.pi ** 2, 3))
test("sgn(cos(PI/4))", 1)
test("sgn(cos(PI/2))", 0)
test("sgn(cos(PI*3/4))", -1)
test("+(sgn(cos(PI/4)))", 1)
test("-(sgn(cos(PI/4)))", -1)


"""
Test output:
>python fourFn.py
9 = 9 ['9'] => ['9']
-9 = -9 ['-', '9'] => ['9', 'unary -']
--9 = 9 ['-', '-', '9'] => ['9', 'unary -', 'unary -']
-E = -2.718281828459045 ['-', 'E'] => ['E', 'unary -']
9 + 3 + 6 = 18 ['9', '+', '3', '+', '6'] => ['9', '3', '+', '6', '+']
9 + 3 / 11 = 9.272727272727273 ['9', '+', '3', '/', '11'] => ['9', '3', '11', '/', '+']
(9 + 3) = 12 [['9', '+', '3']] => ['9', '3', '+']
(9+3) / 11 = 1.0909090909090908 [['9', '+', '3'], '/', '11'] => ['9', '3', '+', '11', '/']
9 - 12 - 6 = -9 ['9', '-', '12', '-', '6'] => ['9', '12', '-', '6', '-']
9 - (12 - 6) = 3 ['9', '-', ['12', '-', '6']] => ['9', '12', '6', '-', '-']
2*3.14159 = 6.28318 ['2', '*', '3.14159'] => ['2', '3.14159', '*']
3.1415926535*3.1415926535 / 10 = 0.9869604400525172 ['3.1415926535', '*', '3.1415926535', '/', '10'] => ['3.1415926535', '3.1415926535', '*', '10', '/']
PI * PI / 10 = 0.9869604401089358 ['PI', '*', 'PI', '/', '10'] => ['PI', 'PI', '*', '10', '/']
PI*PI/10 = 0.9869604401089358 ['PI', '*', 'PI', '/', '10'] => ['PI', 'PI', '*', '10', '/']
PI^2 = 9.869604401089358 ['PI', '^', '2'] => ['PI', '2', '^']
round(PI^2) = 10 [('round', 1), [['PI', '^', '2']]] => ['PI', '2', '^', ('round', 1)]
6.02E23 * 8.048 = 4.844896e+24 ['6.02E23', '*', '8.048'] => ['6.02E23', '8.048', '*']
e / 3 = 0.9060939428196817 ['E', '/', '3'] => ['E', '3', '/']
sin(PI/2) = 1.0 [('sin', 1), [['PI', '/', '2']]] => ['PI', '2', '/', ('sin', 1)]
10+sin(PI/4)^2 = 10.5 ['10', '+', ('sin', 1), [['PI', '/', '4']], '^', '2'] => ['10', 'PI', '4', '/', ('sin', 1), '2', '^', '+']
trunc(E) = 2 [('trunc', 1), [['E']]] => ['E', ('trunc', 1)]
trunc(-E) = -2 [('trunc', 1), [['-', 'E']]] => ['E', 'unary -', ('trunc', 1)]
round(E) = 3 [('round', 1), [['E']]] => ['E', ('round', 1)]
round(-E) = -3 [('round', 1), [['-', 'E']]] => ['E', 'unary -', ('round', 1)]
E^PI = 23.140692632779263 ['E', '^', 'PI'] => ['E', 'PI', '^']
exp(0) = 1.0 [('exp', 1), [['0']]] => ['0', ('exp', 1)]
exp(1) = 2.718281828459045 [('exp', 1), [['1']]] => ['1', ('exp', 1)]
2^3^2 = 512 ['2', '^', '3', '^', '2'] => ['2', '3', '2', '^', '^']
(2^3)^2 = 64 [['2', '^', '3'], '^', '2'] => ['2', '3', '^', '2', '^']
2^3+2 = 10 ['2', '^', '3', '+', '2'] => ['2', '3', '^', '2', '+']
2^3+5 = 13 ['2', '^', '3', '+', '5'] => ['2', '3', '^', '5', '+']
2^9 = 512 ['2', '^', '9'] => ['2', '9', '^']
sgn(-2) = -1 [('sgn', 1), [['-', '2']]] => ['2', 'unary -', ('sgn', 1)]
sgn(0) = 0 [('sgn', 1), [['0']]] => ['0', ('sgn', 1)]
sgn(0.1) = 1 [('sgn', 1), [['0.1']]] => ['0.1', ('sgn', 1)]
foo(0.1) failed eval: invalid identifier 'foo' ['0.1', ('foo', 1)]
round(E, 3) = 2.718 [('round', 2), [['E'], ['3']]] => ['E', '3', ('round', 2)]
round(PI^2, 3) = 9.87 [('round', 2), [['PI', '^', '2'], ['3']]] => ['PI', '2', '^', '3', ('round', 2)]
sgn(cos(PI/4)) = 1 [('sgn', 1), [[('cos', 1), [['PI', '/', '4']]]]] => ['PI', '4', '/', ('cos', 1), ('sgn', 1)]
sgn(cos(PI/2)) = 0 [('sgn', 1), [[('cos', 1), [['PI', '/', '2']]]]] => ['PI', '2', '/', ('cos', 1), ('sgn', 1)]
sgn(cos(PI*3/4)) = -1 [('sgn', 1), [[('cos', 1), [['PI', '*', '3', '/', '4']]]]] => ['PI', '3', '*', '4', '/', ('cos', 1), ('sgn', 1)]
+(sgn(cos(PI/4))) = 1 ['+', [('sgn', 1), [[('cos', 1), [['PI', '/', '4']]]]]] => ['PI', '4', '/', ('cos', 1), ('sgn', 1)]
-(sgn(cos(PI/4))) = -1 ['-', [('sgn', 1), [[('cos', 1), [['PI', '/', '4']]]]]] => ['PI', '4', '/', ('cos', 1), ('sgn', 1), 'unary -']
"""
