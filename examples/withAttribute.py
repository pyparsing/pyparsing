#
#  with_attribute.py
#  Copyright, 2007 - Paul McGuire
#
#  Simple example of using with_attribute parse action helper
#  to define
#
import pyparsing as pp

data = """\
    <td align=right width=80><font size=2 face="New Times Roman,Times,Serif">&nbsp;49.950&nbsp;</font></td>
    <td align=left width=80><font size=2 face="New Times Roman,Times,Serif">&nbsp;50.950&nbsp;</font></td>
    <td align=right width=80><font size=2 face="New Times Roman,Times,Serif">&nbsp;51.950&nbsp;</font></td>
    """

td, tdEnd = pp.make_html_tags("TD")
font, fontEnd = pp.make_html_tags("FONT")
realNum = pp.pyparsing_common.real
NBSP = pp.Literal("&nbsp;")
patt = td + font + NBSP + realNum("value") + NBSP + fontEnd + tdEnd

# always use add_parse_action when adding with_attribute as a parse action to a start tag
td.add_parse_action(pp.with_attribute(align="right", width="80"))

for s in patt.search_string(data):
    print(s.value)
