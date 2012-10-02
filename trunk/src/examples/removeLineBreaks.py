# removeLineBreaks.py
#
# Demonstration of the pyparsing module, converting text files
# with hard line-breaks to text files with line breaks only
# between paragraphs.  (Helps when converting downloads from Project
# Gutenberg - http://www.gutenberg.org - to import to word processing apps 
# that can reformat paragraphs once hard line-breaks are removed.)
#
# Uses parse actions and transformString to remove unwanted line breaks,
# and to double up line breaks between paragraphs.
#
# Copyright 2006, by Paul McGuire
#
from pyparsing import *

# define an expression for the body of a line of text - use a parse action to reject any
# empty lines
def mustBeNonBlank(s,l,t):
    if not t[0]:
        raise ParseException(s,l,"line body can't be empty")
lineBody = SkipTo(lineEnd).setParseAction(mustBeNonBlank)

# now define a line with a trailing lineEnd, to be replaced with a space character
textLine = lineBody + Suppress(lineEnd).setParseAction(replaceWith(" "))

# define a paragraph, with a separating lineEnd, to be replaced with a double newline
para = OneOrMore(textLine) + Suppress(lineEnd).setParseAction(replaceWith("\n\n"))


# run a test
test = """
    Now is the
    time for
    all
    good men
    to come to

    the aid of their
    country.
"""
print para.transformString(test)

# process an entire file
z = para.transformString(file("Successful Methods of Public Speaking.txt").read())
file("Successful Methods of Public Speaking(2).txt","w").write(z)
