#
#  nested.py
#  Copyright, 2007 - Paul McGuire
#
#  Simple example of using nested_expr to define expressions using
#  paired delimiters for grouping lists and sublists
#

from pyparsing import *

data = """
{
     { item1 "item with } in it" }
     {
      {item2a item2b }
      {item3}
     }

}
"""

# use {}'s for nested lists
nestedItems = nested_expr("{", "}")
print((nestedItems + string_end).parse_string(data).as_list())

# use default delimiters of ()'s
mathExpr = nested_expr()
print(mathExpr.parse_string("((( ax + by)*C) *(Z | (E^F) & D))"))
