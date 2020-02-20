import pprint
from pyparsing import ParseException

from examples.verilogParse import Verilog_BNF


def test(strng):
    tokens = []
    try:
        tokens = Verilog_BNF().parseString(strng)
    except ParseException as err:
        print(err.line)
        print(" " * (err.column - 1) + "^")
        print(err)
    return tokens


toptest = """
    module TOP( in, out );
    input [7:0] in;
    output [5:0] out;
    COUNT_BITS8 count_bits( .IN( in ), .C( out ) );
    endmodule"""
pprint.pprint(test(toptest).asList())
