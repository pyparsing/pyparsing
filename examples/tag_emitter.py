#
# tag_emitter.py
#
# Example showing how to inject tags into the parsed results by adding
# an Empty() with a parse action to return the desired added data.
#
# Copyright 2023, Paul McGuire
#
import pyparsing as pp

# define expressions to parse different forms of integer constants
# add parse actions that will evaluate the integer correctly
binary_int = ("0b" + pp.Word("01")).add_parse_action(lambda t: int(t[1], base=2))
hex_int = ("0x" + pp.Word(pp.hexnums)).add_parse_action(lambda t: int(t[1], base=16))
dec_int = pp.Word(pp.nums).add_parse_action(lambda t: int(t[0]))


# define function to inject an expression that will add an extra tag in the
# parsed output, to indicate what the original input format was
def emit_tag(s):
    return pp.Empty().add_parse_action(pp.replace_with(s))


# define a parser that includes the tag emitter for each integer format type
int_parser = (binary_int("value") + emit_tag("binary")("original_format")
              | hex_int("value") + emit_tag("hex")("original_format")
              | dec_int("value") + emit_tag("decimal")("original_format")
              )

# parse some integers
int_parser.run_tests("""\
    0b11011000001
    0x6c1
    1729""")
