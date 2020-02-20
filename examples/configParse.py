#
# configparse.py
#
# an example of using the parsing module to be able to process a .INI configuration file
#
# Copyright (c) 2003, Paul McGuire
#

from pyparsing import (
    Literal,
    Word,
    ZeroOrMore,
    Group,
    Dict,
    Optional,
    printables,
    ParseException,
    restOfLine,
    empty,
)
import pprint


inibnf = None


def inifile_BNF():
    global inibnf

    if not inibnf:

        # punctuation
        lbrack = Literal("[").suppress()
        rbrack = Literal("]").suppress()
        equals = Literal("=").suppress()
        semi = Literal(";")

        comment = semi + Optional(restOfLine)

        nonrbrack = "".join([c for c in printables if c != "]"]) + " \t"
        nonequals = "".join([c for c in printables if c != "="]) + " \t"

        sectionDef = lbrack + Word(nonrbrack) + rbrack
        keyDef = ~lbrack + Word(nonequals) + equals + empty + restOfLine
        # strip any leading or trailing blanks from key
        def stripKey(tokens):
            tokens[0] = tokens[0].strip()

        keyDef.setParseAction(stripKey)

        # using Dict will allow retrieval of named data fields as attributes of the parsed results
        inibnf = Dict(ZeroOrMore(Group(sectionDef + Dict(ZeroOrMore(Group(keyDef))))))

        inibnf.ignore(comment)

    return inibnf
