# vim:fileencoding=utf-8 
#
# greetingInGreek.py
#
# Demonstration of the parsing module, on the prototypical "Hello, World!" example
#
# Copyright 2004-2016, by Paul McGuire
#
from pyparsing import Word 

# define grammar
alphas = ''.join(chr(x) for x in range(0x386, 0x3ce)) 
greet = Word(alphas) + ',' + Word(alphas) + '!' 

# input string
hello = "Καλημέρα, κόσμε!".decode('utf-8') 

# parse input string
print(greet.parseString( hello ))

