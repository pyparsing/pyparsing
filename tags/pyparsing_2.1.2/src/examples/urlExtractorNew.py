# URL extractor
# Copyright 2004, Paul McGuire
from pyparsing import Literal,Suppress,CharsNotIn,CaselessLiteral,\
        Word,dblQuotedString,alphanums,SkipTo,makeHTMLTags
import urllib.request, urllib.parse, urllib.error
import pprint

# Define the pyparsing grammar for a URL, that is:
#    URLlink ::= <a href= URL>linkText</a>
#    URL ::= doubleQuotedString | alphanumericWordPath
# Note that whitespace may appear just about anywhere in the link.  Note also
# that it is not necessary to explicitly show this in the pyparsing grammar; by default,
# pyparsing skips over whitespace between tokens.
linkOpenTag,linkCloseTag = makeHTMLTags("a")
link = linkOpenTag + SkipTo(linkCloseTag).setResultsName("body") + linkCloseTag.suppress()

# Go get some HTML with some links in it.
serverListPage = urllib.request.urlopen( "http://www.google.com" )
htmlText = serverListPage.read()
serverListPage.close()

# scanString is a generator that loops through the input htmlText, and for each
# match yields the tokens and start and end locations (for this application, we are
# not interested in the start and end values).
for toks,strt,end in link.scanString(htmlText):
    print(toks.startA.href,"->",toks.body)

# Create dictionary from list comprehension, assembled from each pair of tokens returned 
# from a matched URL.
pprint.pprint( 
    dict( [ (toks.body,toks.startA.href) for toks,strt,end in link.scanString(htmlText) ] )
    )



