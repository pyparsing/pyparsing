# unicode_denormalizer.py
#
# Demonstration of the pyparsing's transform_string() method, to
# convert identifiers in Python source code to equivalent Unicode
# characters. Python's compiler automatically normalizes Unicode
# characters back to their ASCII equivalents, so that identifiers may
# be rewritten using other Unicode characters, and normalize back to
# the same identifier. For instance, Python treats "print" and "𝕡𝓻ᵢ𝓃𝘁"
# and "𝖕𝒓𝗂𝑛ᵗ" all as the same identifier.
#
# The converter must take care to *only* transform identifiers -
# Python keywords must always be represented in base ASCII form. To
# skip over keywords, they are added to the parser/transformer, but
# contain no transforming parse action.
#
# The converter also detects identifiers in placeholders within f-strings.
#
# Copyright 2022, by Paul McGuire
#
import keyword
import random
import unicodedata

import pyparsing as pp
ppu = pp.pyparsing_unicode

ident_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_0123456789·"

ident_char_map = {}.fromkeys(ident_chars, "")
for ch in ppu.identbodychars:
    normal = unicodedata.normalize("NFKC", ch)
    if normal in ident_char_map:
        ident_char_map[normal] += ch

ligature_map = {
    'ffl': 'ﬄ ﬄ ﬀl fﬂ ffl',
    'ffi': 'ﬃ ﬃ ﬀi fﬁ ffi',
    'ff': 'ﬀ ff',
    'fi': 'ﬁ fi',
    'fl': 'ﬂ fl',

    'ij': 'ij ĳ',
    'lj': 'lj ǉ',
    'nj': 'nj ǌ',
    'dz': 'dz ǳ',
    'ii': 'ii ⅱ',
    'iv': 'iv ⅳ',
    'vi': 'vi ⅵ',
    'ix': 'ix ⅸ',
    'xi': 'xi ⅺ',
}
ligature_transformer = pp.oneOf(ligature_map).add_parse_action(lambda t: random.choice(ligature_map[t[0]].split()))


def make_mixed_font(t):
    t_0 = t[0][0]
    ret = ['_' if t_0 == '_' else random.choice(ident_char_map.get(t_0, t_0))]
    t_rest = ligature_transformer.transform_string(t[0][1:])
    ret.extend(random.choice(ident_char_map.get(c, c)) for c in t_rest)
    return ''.join(ret)


identifier = pp.pyparsing_common.identifier
identifier.add_parse_action(make_mixed_font)

python_quoted_string = pp.Opt(pp.Char("fF")("f_string_prefix")) + (
        pp.quotedString
        | pp.QuotedString('"""', multiline=True, unquoteResults=False)
        | pp.QuotedString("'''", multiline=True, unquoteResults=False)
)("quoted_string_body")


def mix_fstring_expressions(t):
    if not t.f_string_prefix:
        return
    fstring_arg = pp.QuotedString("{", end_quote_char="}")
    fstring_arg.add_parse_action(lambda tt: "{" + transformer.transform_string(tt[0]) + "}")
    ret = t.f_string_prefix + fstring_arg.transform_string(t.quoted_string_body)
    return ret


python_quoted_string.add_parse_action(mix_fstring_expressions)

any_keyword = pp.MatchFirst(map(pp.Keyword, list(keyword.kwlist) + getattr(keyword, "softkwlist", [])))

# quoted strings and keywords will be parsed, but left untransformed
transformer = python_quoted_string | any_keyword | identifier


def demo():
    import textwrap
    hello_source = textwrap.dedent("""
    def hello():
        try:
            hello_ = "Hello"
            world_ = "World"
            print(f"{hello_}, {world_}!")
        except TypeError as exc:
            print("failed: {}".format(exc))
    
    if __name__ == "__main__":
        hello()
    """)
    source = hello_source

    transformed = transformer.transform_string(source)
    print(transformed)

    # does it really work?
    code = compile(transformed, source, mode="exec")
    exec(code)

    if 0:
        # pick some code from the stdlib
        import unittest.util as lib_module
        import inspect
        source = inspect.getsource(lib_module)
        transformed = transformer.transform_string(source)
        print()
        print(transformed)

if __name__ == '__main__':
    demo()
