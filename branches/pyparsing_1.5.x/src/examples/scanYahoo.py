from pyparsing import makeHTMLTags,SkipTo,htmlComment
import urllib

serverListPage = urllib.urlopen( "http://www.yahoo.com" )
htmlText = serverListPage.read()
serverListPage.close()

aStart,aEnd = makeHTMLTags("A")

link = aStart + SkipTo(aEnd).setResultsName("link") + aEnd
link.ignore(htmlComment)

for toks,start,end in link.scanString(htmlText):
    print toks.link, "->", toks.startA.href