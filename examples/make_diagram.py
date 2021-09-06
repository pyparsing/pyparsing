#
# make_diagram.py
#
# Sample railroad diagrams of selected pyparsing examples.
#
# Copyright 2021, Paul McGuire

# Uncomment the related import statement and rerun to construct railroad diagram

from examples.delta_time import time_expression as imported_expr

# from examples.sexpParser import sexp as imported_expr
# from examples.ebnftest import ebnf_parser as imported_expr
# from examples.jsonParser import jsonObject as imported_expr
# from examples.lucene_grammar import expression as imported_expr
# from examples.invRegex import parser; imported_expr = parser()
# from examples.oc import program as imported_expr
# from examples.mozillaCalendarParser import calendars as imported_expr
# from examples.pgn import pgnGrammar as imported_expr
# from examples.idlParse import CORBA_IDL_BNF as imported_expr
# from examples.chemicalFormulas import formula as imported_expr
# from examples.romanNumerals import romanNumeral as imported_expr
# from examples.protobuf_parser import parser as imported_expr
# from examples.parsePythonValue import listItem as imported_expr
# from examples.one_to_ninety_nine import one_to_99 as imported_expr
# from examples.simpleSQL import simpleSQL as imported_expr
# from examples.simpleBool import boolExpr as imported_expr

imported_expr.create_diagram(output_html="output.html")
