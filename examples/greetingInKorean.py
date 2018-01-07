# vim:fileencoding=utf-8 
#
# greetingInKorean.py
#
# Demonstration of the parsing module, on the prototypical "Hello, World!" example
#
# Copyright 2004-2016, by Paul McGuire
#
from pyparsing import Word, srange

koreanChars = srange(r"[\0xac00-\0xd7a3]")
koreanWord = Word(koreanChars,min=2)

# define grammar
greet = koreanWord + "," + koreanWord + "!"

# input string
hello = '\uc548\ub155, \uc5ec\ub7ec\ubd84!' #"Hello, World!" in Korean

# parse input string
print(greet.parseString( hello ))

