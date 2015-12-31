# 
# tagCapture.py
#
# Simple demo showing how to match HTML tags
#

from pyparsing import *

src = "this is test <b> bold <i>text</i> </b> normal text "

def matchingCloseTag(other):
    ret = Forward()
    ret << anyCloseTag.copy()
    
    def setupMatchingClose(tokens):
        opentag = tokens[0]
        
        def mustMatch(tokens):
            if tokens[0][0].strip('<>/') != opentag:
                raise ParseException("",0,"")
                
        ret.setParseAction(mustMatch)
        
    other.addParseAction(setupMatchingClose)
    
    return ret

for m in originalTextFor(anyOpenTag + SkipTo(matchingCloseTag(anyOpenTag), 
                                              include=True,
                                              failOn=anyOpenTag) ).searchString(src):
    print(m.dump())

for m in originalTextFor(anyOpenTag + SkipTo(matchingCloseTag(anyOpenTag), 
                                              include=True) ).searchString(src):
    print(m.dump())
