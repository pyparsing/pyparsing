#
# make_diagram.py
#
# Sample railroad diagrams of selected pyparsing examples.
#
# Copyright 2020, Paul McGuire

from pyparsing.diagram import to_railroad, railroad_to_html


def make_diagram(expr, output_html="output.html"):
    with open(output_html, "w", encoding="utf-8") as fp:
        railroad = to_railroad(expr)
        fp.write(railroad_to_html(railroad))


# Uncomment the related import statement and rerun to construct railroad diagram

from examples.delta_time import time_expression as imported_expr

# from examples.sexpParser import sexp as imported_expr
# from examples.ebnftest import ebnf_parser as imported_expr
# from examples.jsonParser import jsonObject as imported_expr
# from examples.lucene_grammar import expression as imported_expr
# from examples.invRegex import parser as imported_expr
# from examples.oc import program as imported_expr
# from examples.mozillaCalendarParser import calendars as imported_expr
# from examples.pgn import pgnGrammar as imported_expr
# from examples.idlParse import CORBA_IDL_BNF as imported_expr
# from examples.chemicalFormulas import formula as imported_expr
# from examples.romanNumerals import romanNumeral as imported_expr
# from examples.protobuf_parser import parser as imported_expr
# from examples.parsePythonValue import listItem as imported_expr

make_diagram(imported_expr)
