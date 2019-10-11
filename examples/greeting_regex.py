# greeting.py
#
# Demonstration of the pyparsing module, on the prototypical "Hello, World!"
# example
#
# Copyright 2003, 2019 by Paul McGuire
#
import pyparsing as pp
from pyparsing import Regex


# define grammar
color = Regex(r"\b(orange){e<=1}\b")
greet = pp.Word(pp.alphas) + "," + pp.Word(pp.alphas) + "," + color + "!" + pp.lineEnd()

# input string
hello = "Hello, World, orange!"

# parse input string
print(hello, "->", greet.parseString(hello))

# parse a bunch of input strings
greet.runTests("""\
    Hello, World, orange!
    Ahoy, Matey,  oranges!
    Howdy, Pardner, orage!
    Morning, Neighbor, orge!
    """)