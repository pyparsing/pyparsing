#
# make_diagram.py
#
# Sample railroad diagrams of selected pyparsing examples.
#
# Copyright 2020, Paul McGuire

from pyparsing.diagram import to_railroad, railroad_to_html


def make_diagram(expr):
    with open("output.html", "w", encoding="utf-8") as fp:
        railroad = to_railroad(expr)
        fp.write(railroad_to_html(railroad))


# Uncomment the related import statement, and pass the imported parser to make_diagram

# from examples.delta_time import time_expression
# from examples.sexpParser import sexp
# from examples.ebnftest import ebnf_parser
# from examples.jsonParser import jsonObject
# from examples.lucene_grammar import expression
# from examples.invRegex import parser
# from examples.oc import program
# from examples.mozillaCalendarParser import calendars
# from examples.pgn import pgnGrammar
# from examples.idlParse import CORBA_IDL_BNF
# from examples.chemicalFormulas import formula
# from examples.romanNumerals import romanNumeral
# from examples.protobuf_parser import parser
from examples.parsePythonValue import listItem

make_diagram(listItem)
