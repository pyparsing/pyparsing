# listAllMatches.py
#
# Sample program showing how/when to use listAllMatches to get all matching tokens in a results name.
#
# copyright 2006, Paul McGuire
#

from pyparsing import one_of, OneOrMore, printables, StringEnd

test = "The quick brown fox named 'Aloysius' lives at 123 Main Street (and jumps over lazy dogs in his spare time)."
nonAlphas = [c for c in printables if not c.isalpha()]

print("Extract vowels, consonants, and special characters from this test string:")
print("'" + test + "'")
print("")

print("Define grammar using normal results names")
print("(only last matching symbol is saved)")
vowels = one_of(list("aeiouy"), caseless=True)("vowels")
cons = one_of(list("bcdfghjklmnpqrstvwxz"), caseless=True)("cons")
other = one_of(nonAlphas)("others")
letters = OneOrMore(cons | vowels | other) + StringEnd()

results = letters.parse_string(test)
print(results)
print(results.vowels)
print(results.cons)
print(results.others)
print("")


print("Define grammar using results names, with list_all_matches=True")
print("(all matching symbols are saved)")
vowels = one_of(list("aeiouy"), caseless=True)("vowels*")
cons = one_of(list("bcdfghjklmnpqrstvwxz"), caseless=True)("cons*")
other = one_of(nonAlphas)("others*")

letters = OneOrMore(cons | vowels | other)

results = letters.parse_string(test, parse_all=True)
print(results)
print(sorted(set(results)))
print("")
print(results.vowels)
print(sorted(set(results.vowels)))
print("")
print(results.cons)
print(sorted(set(results.cons)))
print("")
print(results.others)
print(sorted(set(results.others)))
