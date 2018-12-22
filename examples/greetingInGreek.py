# vim:fileencoding=utf-8
#
# greetingInGreek.py
#
# Demonstration of the parsing module, on the prototypical "Hello, World!" example
#
# Copyright 2004-2016, by Paul McGuire
#
from pyparsing import Word, pyparsing_unicode

# define grammar
alphas = pyparsing_unicode.Greek.alphas
greet = Word(alphas) + ',' + Word(alphas) + '!'

# input string
hello = "Καλημέρα, κόσμε!"

# parse input string
print(greet.parseString(hello))
