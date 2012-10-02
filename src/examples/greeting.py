# greeting.py
#
# Demonstration of the pyparsing module, on the prototypical "Hello, World!"
# example
#
# Copyright 2003, by Paul McGuire
#
from pyparsing import Word, alphas

# define grammar
greet = Word( alphas ) + "," + Word( alphas ) + "!"

# input string
hello = "Hello, World!"

# parse input string
print hello, "->", greet.parseString( hello )
