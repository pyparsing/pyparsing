# URL extractor
# Copyright 2004, Paul McGuire
from pyparsing import Literal,Suppress,CharsNotIn,CaselessLiteral,\
        Word,dblQuotedString,alphanums,SkipTo
import urllib.request, urllib.parse, urllib.error
import pprint

# Define the pyparsing grammar for a URL, that is:
#    URLlink ::= <a href= URL>linkText</a>
#    URL ::= doubleQuotedString | alphanumericWordPath
# Note that whitespace may appear just about anywhere in the link.  Note also
# that it is not necessary to explicitly show this in the pyparsing grammar; by default,
# pyparsing skips over whitespace between tokens.
linkOpenTag = (Literal("<") + "a" + "href" + "=").suppress() + \
                ( dblQuotedString | Word(alphanums+"/") ) + \
                Suppress(">") 
linkCloseTag = Literal("<") + "/" + CaselessLiteral("a") + ">"
link = linkOpenTag + SkipTo(linkCloseTag) + linkCloseTag.suppress()

# Go get some HTML with some links in it.
serverListPage = urllib.request.urlopen( "http://www.yahoo.com" )
htmlText = serverListPage.read()
serverListPage.close()

# scanString is a generator that loops through the input htmlText, and for each
# match yields the tokens and start and end locations (for this application, we are
# not interested in the start and end values).
for toks,strt,end in link.scanString(htmlText):
    print(toks.asList())

# Rerun scanString, but this time create a dict of text:URL key-value pairs.
# Need to reverse the tokens returned by link, using a parse action.
link.setParseAction( lambda st,loc,toks: [ toks[1], toks[0] ] )
    
# Create dictionary from list comprehension, assembled from each pair of tokens returned 
# from a matched URL.
pprint.pprint( 
    dict( [ toks for toks,strt,end in link.scanString(htmlText) ] )
    )



