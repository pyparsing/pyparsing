# romanNumerals.py
#
# Copyright (c) 2006, 2019, Paul McGuire
#

import pyparsing as pp


def romanNumeralLiteral(numeralString, value):
    return pp.Literal(numeralString).setParseAction(pp.replaceWith(value))


one = romanNumeralLiteral("I", 1)
four = romanNumeralLiteral("IV", 4)
five = romanNumeralLiteral("V", 5)
nine = romanNumeralLiteral("IX", 9)
ten = romanNumeralLiteral("X", 10)
forty = romanNumeralLiteral("XL", 40)
fifty = romanNumeralLiteral("L", 50)
ninety = romanNumeralLiteral("XC", 90)
onehundred = romanNumeralLiteral("C", 100)
fourhundred = romanNumeralLiteral("CD", 400)
fivehundred = romanNumeralLiteral("D", 500)
ninehundred = romanNumeralLiteral("CM", 900)
onethousand = romanNumeralLiteral("M", 1000)

numeral = (
    onethousand
    | ninehundred
    | fivehundred
    | fourhundred
    | onehundred
    | ninety
    | fifty
    | forty
    | ten
    | nine
    | five
    | four
    | one
).leaveWhitespace()

romanNumeral = numeral[1, ...].setParseAction(sum)

# unit tests
def makeRomanNumeral(n):
    def addDigits(n, limit, c, s):
        while n >= limit:
            n -= limit
            s += c
        return n, s

    ret = ""
    n, ret = addDigits(n, 1000, "M", ret)
    n, ret = addDigits(n, 900, "CM", ret)
    n, ret = addDigits(n, 500, "D", ret)
    n, ret = addDigits(n, 400, "CD", ret)
    n, ret = addDigits(n, 100, "C", ret)
    n, ret = addDigits(n, 90, "XC", ret)
    n, ret = addDigits(n, 50, "L", ret)
    n, ret = addDigits(n, 40, "XL", ret)
    n, ret = addDigits(n, 10, "X", ret)
    n, ret = addDigits(n, 9, "IX", ret)
    n, ret = addDigits(n, 5, "V", ret)
    n, ret = addDigits(n, 4, "IV", ret)
    n, ret = addDigits(n, 1, "I", ret)
    return ret


# make a string of all roman numerals from I to MMMMM
tests = " ".join(makeRomanNumeral(i) for i in range(1, 5000 + 1))

# parse each roman numeral, and populate map for validation below
roman_int_map = {}
for expected, (t, s, e) in enumerate(romanNumeral.scanString(tests), start=1):
    orig = tests[s:e]
    if t[0] != expected:
        print("{} {} {}".format("==>", t, orig))
    roman_int_map[orig] = t[0]


def verify_value(s, tokens):
    expected = roman_int_map[s]
    if tokens[0] != expected:
        raise Exception(
            "incorrect value for {} ({}), expected {}".format(s, tokens[0], expected)
        )


romanNumeral.runTests(
    """\
    XVI
    XXXIX
    XIV
    XIX
    MCMLXXX
    MMVI
    MMMMM
    """,
    fullDump=False,
    postParse=verify_value,
)
