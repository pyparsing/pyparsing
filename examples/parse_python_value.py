# parsePythonValue.py
#
# Copyright, 2006, by Paul McGuire
#
import pyparsing as pp


cvtBool = lambda t: t[0] == "True"
cvtInt = lambda toks: int(toks[0])
cvtReal = lambda toks: float(toks[0])
cvtTuple = lambda toks: tuple(toks.as_list())
cvtSet = lambda toks: set(toks.as_list())
cvtDict = lambda toks: dict(toks.as_list())
cvtList = lambda toks: [toks.as_list()]

# define punctuation as suppressed literals
lparen, rparen, lbrack, rbrack, lbrace, rbrace, colon, comma = pp.Suppress.using_each("()[]{}:,")

integer = pp.Regex(r"[+-]?\d+").set_name("integer").add_parse_action(cvtInt)
real = pp.Regex(r"[+-]?\d+\.\d*([Ee][+-]?\d+)?").set_name("real").add_parse_action(cvtReal)
tuple_str = pp.Forward().set_name("tuple_expr")
list_str = pp.Forward().set_name("list_expr")
set_str = pp.Forward().set_name("set_expr")
dict_str = pp.Forward().set_name("dict_expr")

unistr = pp.unicodeString().add_parse_action(lambda t: t[0][2:-1])
quoted_str = pp.quotedString().add_parse_action(lambda t: t[0][1:-1])
bool_literal = pp.oneOf("True False", as_keyword=True).add_parse_action(cvtBool)
none_literal = pp.Keyword("None").add_parse_action(pp.replace_with(None))

list_item = (
    real
    | integer
    | quoted_str
    | unistr
    | bool_literal
    | none_literal
    | pp.Group(list_str)
    | tuple_str
    | set_str
    | dict_str
).set_name("list_item")

tuple_str <<= (
    lparen + pp.Opt(pp.DelimitedList(list_item, allow_trailing_delim=True)) + rparen
)
tuple_str.add_parse_action(cvtTuple)

set_str <<= (
    lbrace + pp.DelimitedList(list_item, allow_trailing_delim=True) + rbrace
)
set_str.add_parse_action(cvtSet)

list_str <<= (
    lbrack + pp.Opt(pp.DelimitedList(list_item, allow_trailing_delim=True)) + rbrack
)
list_str.add_parse_action(cvtList, lambda t: t[0])

dict_entry = pp.Group(list_item + colon + list_item).set_name("dict_entry")
dict_str <<= (
    lbrace + pp.Opt(pp.DelimitedList(dict_entry, allow_trailing_delim=True)) + rbrace
)
dict_str.add_parse_action(cvtDict)

if __name__ == "__main__":

    tests = """['a', 100, ('A', [101,102]), 3.14, [ +2.718, 'xyzzy', -1.414] ]
               [{0: [2], 1: []}, {0: [], 1: [], 2: []}, {0: [1, 2]}]
               { 'A':1, 'B':2, 'C': {'a': 1.2, 'b': 3.4} }
               { 1, 2, 11, "blah" }
               { 'A':1, 'B':2, 'C': {'a', 1.2, 'b', 3.4} }
               3.14159
               42
               6.02E23
               6.02e+023
               1.0e-7
               'a quoted string'"""

    list_item.run_tests(tests)
    list_item.create_diagram("parse_python_value.html")
