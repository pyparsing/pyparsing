import pyparsing as pp

ppc = pp.pyparsing_common

# fmt: off
word = pp.Word(pp.alphas).set_name("word")
integer = pp.Word(pp.nums).set_name("integer")
plus_minus = pp.Char("+-").set_name("add_sub")
mult_div = pp.Char("*/").set_name("mult_div")
street_address = pp.Group(integer("house_number")
                          + word[1, ...]("street_name")
                          ).set_name("street_address")
time = pp.Regex(r"\d\d:\d\d")

grammar = (pp.Group(integer[1, ...])
           + (ppc.ipv4_address
              & word("header_word")
              & pp.Optional(time)
              ).set_name("header with various elements")("header")
           + street_address("address")
           + pp.Group(pp.counted_array(word))
           + pp.Group(integer * 8)("data")
           + pp.Group(pp.Word("abc") + pp.Word("def")*3)
           + pp.infix_notation(integer,
                               [
                                   (plus_minus().set_name("pos_neg"), 1, pp.OpAssoc.RIGHT),
                                   (mult_div, 2, pp.OpAssoc.LEFT),
                                   (plus_minus, 2, pp.OpAssoc.LEFT),
                               ]).set_name("simple_arithmetic")
           + ...
           + pp.Group(ppc.ipv4_address)("ip_address")
           ).set_name("grammar")


grammar.create_diagram("railroad_diagram_demo.html", vertical=4, show_results_names=True)

test = """\
    1 2 3 
    ABC 1.2.3.4 12:45
    123 Main St 
    4
    abc def ghi jkl 
    5 5 5 5 5 5 5 5 
    a d d d 
    2+2 
    alice bob charlie dave 5.6.7.8"""
result = grammar.run_tests([test])
