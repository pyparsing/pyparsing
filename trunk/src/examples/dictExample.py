#
# dictExample.py
#
#  Illustration of using pyparsing's Dict class to process tabular data
#
# Copyright (c) 2003, Paul McGuire
#
from pyparsing import Literal, Word, Group, Dict, ZeroOrMore, alphas, nums, delimitedList
import pprint

testData = """
+-------+------+------+------+------+------+------+------+------+
|       |  A1  |  B1  |  C1  |  D1  |  A2  |  B2  |  C2  |  D2  |
+=======+======+======+======+======+======+======+======+======+
| min   |   7  |  43  |   7  |  15  |  82  |  98  |   1  |  37  |
| max   |  11  |  52  |  10  |  17  |  85  | 112  |   4  |  39  |
| ave   |   9  |  47  |   8  |  16  |  84  | 106  |   3  |  38  |
| sdev  |   1  |   3  |   1  |   1  |   1  |   3  |   1  |   1  |
+-------+------+------+------+------+------+------+------+------+
"""

# define grammar for datatable
heading = (Literal(
"+-------+------+------+------+------+------+------+------+------+") + 
"|       |  A1  |  B1  |  C1  |  D1  |  A2  |  B2  |  C2  |  D2  |" + 
"+=======+======+======+======+======+======+======+======+======+").suppress()
vert = Literal("|").suppress()
number = Word(nums)
rowData = Group( vert + Word(alphas) + vert + delimitedList(number,"|") + vert )
trailing = Literal(
"+-------+------+------+------+------+------+------+------+------+").suppress()

datatable = heading + Dict( ZeroOrMore(rowData) ) + trailing

# now parse data and print results
data = datatable.parseString(testData)
print(data)
pprint.pprint(data.asList())
print("data keys=", list(data.keys()))
print("data['min']=", data['min'])
print("data.max", data.max)
