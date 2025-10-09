#
# scanExamples.py
#
#  Illustration of using pyparsing's scan_string,transform_string, and search_string methods
#
# Copyright (c) 2004, 2006 Paul McGuire
#
from pyparsing import (
    Word,
    alphas,
    alphanums,
    Literal,
    rest_of_line,
    OneOrMore,
    empty,
    Suppress,
    replace_with,
)

# simulate some C++ code
testData = """
#define MAX_LOCS=100
#define USERNAME = "floyd"
#define PASSWORD = "swordfish"

a = MAX_LOCS;
CORBA::initORB("xyzzy", USERNAME, PASSWORD );

"""

#################
print("Example of an extractor")
print("----------------------")

# simple grammar to match #define's
ident = Word(alphas, alphanums + "_")
macroDef = (
    Literal("#define")
    + ident.set_results_name("name")
    + "="
    + rest_of_line.set_results_name("value")
)
for t, s, e in macroDef.scan_string(testData):
    print(t.name, ":", t.value)

# or a quick way to make a dictionary of the names and values
# (return only key and value tokens, and construct dict from key-value pairs)
# - empty ahead of rest_of_line advances past leading whitespace, does implicit lstrip during parsing
macroDef = Suppress("#define") + ident + Suppress("=") + empty + rest_of_line
macros = dict(list(macroDef.search_string(testData)))
print("macros =", macros)
print()


#################
print("Examples of a transformer")
print("----------------------")

# convert C++ namespaces to mangled C-compatible names
scopedIdent = ident + OneOrMore(Literal("::").suppress() + ident)
scopedIdent.set_parse_action(lambda t: "_".join(t))

print("(replace namespace-scoped names with C-compatible names)")
print(scopedIdent.transform_string(testData))


# or a crude pre-processor (use parse actions to replace matching text)
def substituteMacro(s, l, t):
    if t[0] in macros:
        return macros[t[0]]


ident.set_parse_action(substituteMacro)
ident.ignore(macroDef)

print("(simulate #define pre-processor)")
print(ident.transform_string(testData))


#################
print("Example of a stripper")
print("----------------------")

from pyparsing import dbl_quoted_string, LineStart

# remove all string macro definitions (after extracting to a string resource table?)
stringMacroDef = Literal("#define") + ident + "=" + dbl_quoted_string + LineStart()
stringMacroDef.set_parse_action(replace_with(""))

print(stringMacroDef.transform_string(testData))
