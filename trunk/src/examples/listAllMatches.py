# listAllMatches.py
#
# Sample program showing how/when to use listAllMatches to get all matching tokens in a results name.
#
# copyright 2006, Paul McGuire
#

from pyparsing import oneOf, OneOrMore, printables, StringEnd

test = "The quick brown fox named 'Aloysius' lives at 123 Main Street (and jumps over lazy dogs in his spare time)."
nonAlphas = [ c for c in printables if not c.isalpha() ]

print "Extract vowels, consonants, and special characters from this test string:"
print "'" + test + "'"
print

print "Define grammar using normal results names"
print "(only last matching symbol is saved)"
vowels = oneOf(list("aeiouy"), caseless=True).setResultsName("vowels")
cons = oneOf(list("bcdfghjklmnpqrstvwxz"), caseless=True).setResultsName("cons")
other = oneOf(list(nonAlphas)).setResultsName("others")
letters = OneOrMore(cons | vowels | other) + StringEnd()

results = letters.parseString(test)
print results
print results.vowels
print results.cons
print results.others
print


print "Define grammar using results names, with listAllMatches=True"
print "(all matching symbols are saved)"
vowels = oneOf(list("aeiouy"), caseless=True).setResultsName("vowels",listAllMatches=True)
cons = oneOf(list("bcdfghjklmnpqrstvwxz"), caseless=True).setResultsName("cons",listAllMatches=True)
other = oneOf(list(nonAlphas)).setResultsName("others",listAllMatches=True)

letters = OneOrMore(cons | vowels | other) + StringEnd()

results = letters.parseString(test)
print results
print sorted(list(set(results)))
print
print results.vowels
print sorted(list(set(results.vowels)))
print
print results.cons
print sorted(list(set(results.cons)))
print
print results.others
print sorted(list(set(results.others)))

