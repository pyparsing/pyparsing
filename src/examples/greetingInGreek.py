# vim:fileencoding=utf-8 
#
# greetingInGreek.py
#
# Demonstration of the parsing module, on the prototypical "Hello, World!" example
#
from pyparsing import Word 

# define grammar
alphas = u''.join(unichr(x) for x in xrange(0x386, 0x3ce)) 
greet = Word(alphas) + u',' + Word(alphas) + u'!' 

# input string
hello = "Καλημέρα, κόσμε!".decode('utf-8') 

# parse input string
print greet.parseString( hello )

