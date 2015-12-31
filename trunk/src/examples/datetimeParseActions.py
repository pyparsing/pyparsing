# parseActions.py
#
#   A sample program a parser to match a date string of the form "YYYY/MM/DD",
# and return it as a datetime, or raise an exception if not a valid date.
#
# Copyright 2012, Paul T. McGuire
#
from datetime import datetime
from pyparsing import *

# define an integer string, and a parse action to convert it
# to an integer at parse time
integer = Word(nums).setName("integer")
def convertToInt(tokens):
    # no need to test for validity - we can't get here
    # unless tokens[0] contains all numeric digits
    return int(tokens[0])
integer.setParseAction(convertToInt)
# or can be written as one line as
#integer = Word(nums).setParseAction(lambda t: int(t[0]))

# define a pattern for a year/month/day date
date_expr = integer('year') + '/' + integer('month') + '/' + integer('day')

def convertToDatetime(s,loc,tokens):
    try:
        # note that the year, month, and day fields were already
        # converted to ints from strings by the parse action defined
        # on the integer expression above
        return datetime(tokens.year, tokens.month, tokens.day).date()
    except Exception as ve:
        errmsg = "'%d/%d/%d' is not a valid date, %s" % \
            (tokens.year, tokens.month, tokens.day, ve)
        raise ParseException(s, loc, errmsg)
date_expr.setParseAction(convertToDatetime)


date_expr.runTests("""\
    2000/1/1 
    2000/13/1  # invalid month
    1900/2/29  # 1900 was not a leap year
    2000/2/29  # but 2000 was
    """)