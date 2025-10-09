#
# indented_block_example.py
#

import pyparsing as pp

ppc = pp.pyparsing_common

data = """\

    A
        100
        101

        102
    B
        200
        201
    
    C
        300

"""

integer = ppc.integer
group = pp.Group(pp.Char(pp.alphas) + pp.Group(pp.IndentedBlock(integer)))

print(group[...].parse_string(data).dump())

# example of a recursive IndentedBlock

data = """\

    A
        100
        101

        102
    B
        200
        b
            210
            211
        202
    C
        300

"""

group = pp.Forward()
group <<= pp.Group(pp.Char(pp.alphas) + pp.Group(pp.IndentedBlock(integer | group)))

print("using search_string")
print(sum(group.search_string(data)).dump())
