#
#  withAttribute.py
#  Copyright, 2007 - Paul McGuire
#
#  Simple example of using withAttribute parse action helper
#  to define 
#
data = """\
    <td align=right width=80><font size=2 face="New Times Roman,Times,Serif">&nbsp;49.950&nbsp;</font></td>
    <td align=left width=80><font size=2 face="New Times Roman,Times,Serif">&nbsp;50.950&nbsp;</font></td>
    <td align=right width=80><font size=2 face="New Times Roman,Times,Serif">&nbsp;51.950&nbsp;</font></td>
    """

from pyparsing import *

tdS,tdE = makeHTMLTags("TD")
fontS,fontE = makeHTMLTags("FONT")
realNum = Combine( Word(nums) + "." + Word(nums) ).setParseAction(lambda t:float(t[0]))
NBSP = Literal("&nbsp;")
patt = tdS + fontS + NBSP + realNum("value") + NBSP + fontE + tdE

tdS.setParseAction( withAttribute(align="right",width="80") )
for s in patt.searchString(data):
    print(s.value)
