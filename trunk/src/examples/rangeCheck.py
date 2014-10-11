# rangeCheck.py
#
#   A sample program showing how parse actions can convert parsed 
# strings into a data type or object, and to validate the parsed value.
#
# Copyright 2011, Paul T. McGuire
#

from pyparsing import Word, nums, Suppress, ParseException, empty, Optional
from datetime import datetime

def rangeCheck(minval=None, maxval=None):
    # have to specify at least one range boundary
    if minval is None and maxval is None:
        raise ValueError("minval or maxval must be specified")
        
    # set range testing function and error message depending on
    # whether either or both min and max values are given
    inRangeFn = {
        (True, False)  : lambda x : x <= maxval,
        (False, True)  : lambda x : minval <= x,
        (False, False) : lambda x : minval <= x <= maxval,
        }[minval is None, maxval is None]
    outOfRangeMessage = {
        (True, False)  : "value %%s is greater than %s" % maxval,
        (False, True)  : "value %%s is less than %s" % minval,
        (False, False) : "value %%s is not in the range (%s to %s)" % (minval,maxval),
        }[minval is None, maxval is None]

    # define the actual range checking parse action
    def rangeCheckParseAction(string, loc, tokens):
        parsedval = tokens[0]
        if not inRangeFn(parsedval):
            raise ParseException(string, loc, outOfRangeMessage % parsedval)

    return rangeCheckParseAction

# define the expressions for a date of the form YYYY/MM/DD or YYYY/MM (assumes YYYY/MM/01)
integer = Word(nums).setName("integer")
integer.setParseAction(lambda t:int(t[0]))

month = integer.copy().addParseAction(rangeCheck(1,12))
day = integer.copy().addParseAction(rangeCheck(1,31))
year = integer.copy().addParseAction(rangeCheck(2000, None))

SLASH = Suppress('/')
dateExpr = year("year") + SLASH + month("month") + Optional(SLASH + day("day"))
dateExpr.setName("date")

# convert date fields to datetime (also validates dates as truly valid dates)
dateExpr.setParseAction(lambda t: datetime(t.year, t.month, t.day or 1).date())

# add range checking on dates
mindate = datetime(2002,1,1).date()
maxdate = datetime.now().date()
dateExpr.addParseAction(rangeCheck(mindate, maxdate))


tests = """
    2011/5/8
    2001/1/1
    2004/2/29
    2004/2/30
    2004/2
    """.splitlines()
for t in tests:
    t = t.strip()
    if not t: continue
    print(t)
    try:
        print(dateExpr.parseString(t)[0])
    except Exception as e:
        print(str(e))
    print()


