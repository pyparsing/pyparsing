import pyparsing as pp
ppc = pp.pyparsing_common

word = pp.Word(pp.alphas).setName("word")
integer = pp.Word(pp.nums).setName("integer")
plus_minus = pp.Char("+-")
mult_div = pp.Char("*/")
street_address = pp.Group(integer("house_number") + word[1, ...]("street_name")).setName("street_address")

grammar = (integer[1, ...]
           + (ppc.ipv4_address & word & pp.Optional(integer)).setName("header with various elements")("header")
           + street_address("address")
           + pp.Group(pp.counted_array(word))
           + pp.Group(integer * 8)("data")
           + pp.infix_notation(integer,
                               [
                                   (plus_minus().setName("leading sign"), 1, pp.opAssoc.RIGHT),
                                   (mult_div, 2, pp.opAssoc.LEFT),
                                   (plus_minus, 2, pp.opAssoc.LEFT),
                               ]).setName("simple_arithmetic")
           + ...
           + pp.Group(ppc.ipv4_address)("ip_address")
           ).setName("grammar")


grammar.create_diagram("railroad_diagram_demo.html", vertical=6, show_results_names=True)
