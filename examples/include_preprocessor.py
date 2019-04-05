#
# include_preprocessor.py
#
# Short pyparsing script to perform #include inclusions similar to the C preprocessor
#
# Copyright 2019, Paul McGuire
#
import pyparsing as pp
from pathlib import Path

SEMI = pp.Suppress(';')
INCLUDE = pp.Keyword("#include")
quoted_string = pp.quotedString.addParseAction(pp.removeQuotes)

include_directive = (INCLUDE
                     + (quoted_string
                        | pp.Word(pp.printables, excludeChars=';'))("include_file")
                     + SEMI)

# add parse action that will recursively pull in included files
seen = set()
def read_include_contents(s, l, t):
    include_file_ref = t.include_file
    include_echo = "/* {} */".format(pp.line(l, s).strip())

    # guard against recursive includes
    if include_file_ref not in seen:
        seen.add(include_file_ref)
        return (include_echo + '\n'
                + include_directive.transformString(Path(include_file_ref).read_text()))
    else:
        lead = ' '*(pp.col(l, s) - 1)
        return "/* recursive include! */\n{}{}".format(lead, include_echo)

# attach include processing method as parse action to include_directive expression
include_directive.addParseAction(read_include_contents)


if __name__ == '__main__':

    # demo

    # create test files
    Path('a.txt').write_text("""\
    /* a.txt */
    int i;
    
    #include b.txt;
    """)

    Path('b.txt').write_text("""\
    i = 100;
    #include 'c.txt';
    """)

    Path('c.txt').write_text("""\
    i += 1;
    
    #include b.txt;
    """)


    # use include_directive.transformString to perform includes

    # read contents of original file
    initial_file = Path('a.txt').read_text()

    # print original file
    print(initial_file)
    print('-----------------')

    # print expanded file
    print(include_directive.transformString(initial_file))

    # clean up
    for fname in "a.txt b.txt c.txt".split():
        Path(fname).unlink()
