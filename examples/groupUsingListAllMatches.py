#
# A simple example showing the use of the implied list_all_matches=True for
# results names with a trailing '*' character.
#
# This example performs work similar to itertools.groupby, but without
# having to sort the input first.
#
# Copyright 2004-2016, by Paul McGuire
#
from pyparsing import Word, ZeroOrMore, nums

aExpr = Word("A", nums)
bExpr = Word("B", nums)
cExpr = Word("C", nums)
grammar = ZeroOrMore(aExpr("A*") | bExpr("B*") | cExpr("C*"))

grammar.run_tests("A1 B1 A2 C1 B2 A3")
