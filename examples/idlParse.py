#
# idlparse.py
#
# an example of using the parsing module to be able to process a subset of the CORBA IDL grammar
#
# Copyright (c) 2003, Paul McGuire
#

from pyparsing import (
    Literal,
    Word,
    OneOrMore,
    ZeroOrMore,
    Forward,
    DelimitedList,
    Group,
    Optional,
    alphas,
    rest_of_line,
    c_style_comment,
    alphanums,
    quoted_string,
    ParseException,
    Keyword,
    Regex,
)
import pprint

# ~ import tree2image

bnf = None


def CORBA_IDL_BNF():
    global bnf

    if not bnf:

        # punctuation
        (
            colon,
            lbrace,
            rbrace,
            lbrack,
            rbrack,
            lparen,
            rparen,
            equals,
            comma,
            dot,
            slash,
            bslash,
            star,
            semi,
            langle,
            rangle,
        ) = map(Literal, r":{}[]()=,./\*;<>")

        # keywords
        (
            any_,
            attribute_,
            boolean_,
            case_,
            char_,
            const_,
            context_,
            default_,
            double_,
            enum_,
            exception_,
            FALSE_,
            fixed_,
            float_,
            inout_,
            interface_,
            in_,
            long_,
            module_,
            Object_,
            octet_,
            oneway_,
            out_,
            raises_,
            readonly_,
            sequence_,
            short_,
            string_,
            struct_,
            switch_,
            TRUE_,
            typedef_,
            unsigned_,
            union_,
            void_,
            wchar_,
            wstring_,
        ) = map(
            Keyword,
            """any attribute boolean case char const context
            default double enum exception FALSE fixed float inout interface in long module
            Object octet oneway out raises readonly sequence short string struct switch
            TRUE typedef unsigned union void wchar wstring""".split(),
        )

        identifier = Word(alphas, alphanums + "_").set_name("identifier")

        real = Regex(r"[+-]?\d+\.\d*([Ee][+-]?\d+)?").set_name("real")
        integer = Regex(r"0x[0-9a-fA-F]+|[+-]?\d+").set_name("int")

        udTypeName = DelimitedList(identifier, "::", combine=True).set_name("udType")
        typeName = (
            any_
            | boolean_
            | char_
            | double_
            | fixed_
            | float_
            | long_
            | octet_
            | short_
            | string_
            | wchar_
            | wstring_
            | udTypeName
        ).set_name("type")
        sequenceDef = Forward().set_name("seq")
        sequenceDef << Group(sequence_ + langle + (sequenceDef | typeName) + rangle)
        typeDef = sequenceDef | (typeName + Optional(lbrack + integer + rbrack))
        typedefDef = Group(typedef_ + typeDef + identifier + semi).set_name("typedef")

        moduleDef = Forward().set_name("moduleDef")
        constDef = Group(
            const_
            + typeDef
            + identifier
            + equals
            + (real | integer | quoted_string)
            + semi
        ).set_name(
            "constDef"
        )  # | quoted_string )
        exceptionItem = Group(typeDef + identifier + semi)
        exceptionDef = (
            exception_ + identifier + lbrace + ZeroOrMore(exceptionItem) + rbrace + semi
        ).set_name("exceptionDef")
        attributeDef = Optional(readonly_) + attribute_ + typeDef + identifier + semi
        paramlist = DelimitedList(
            Group((inout_ | in_ | out_) + typeName + identifier)
        ).set_name("paramlist")
        operationDef = (
            (void_ ^ typeDef)
            + identifier
            + lparen
            + Optional(paramlist)
            + rparen
            + Optional(raises_ + lparen + Group(DelimitedList(typeName)) + rparen)
            + semi
        ).set_name("operationDef")
        interfaceItem = constDef | exceptionDef | attributeDef | operationDef
        interfaceDef = Group(
            interface_
            + identifier
            + Optional(colon + DelimitedList(typeName))
            + lbrace
            + ZeroOrMore(interfaceItem)
            + rbrace
            + semi
        ).set_name("interfaceDef")
        moduleItem = (
            interfaceDef | exceptionDef | constDef | typedefDef | moduleDef
        ).set_name("moduleItem")
        (
            moduleDef
            << module_ + identifier + lbrace + ZeroOrMore(moduleItem) + rbrace + semi
        )

        bnf = moduleDef | OneOrMore(moduleItem)

        singleLineComment = "//" + rest_of_line
        bnf.ignore(singleLineComment)
        bnf.ignore(c_style_comment)

    return bnf


if __name__ == "__main__":

    testnum = 1

    def test(strng):
        global testnum
        print(strng)
        try:
            bnf = CORBA_IDL_BNF()
            tokens = bnf.parse_string(strng)
            print("tokens = ")
            pprint.pprint(tokens.as_list())
            imgname = "idlParse%02d.bmp" % testnum
            testnum += 1
            # ~ tree2image.str2image( str(tokens.as_list()), imgname )
        except ParseException as err:
            print(err.line)
            print(" " * (err.column - 1) + "^")
            print(err)
        print()

    test(
        """
        /*
         * a block comment *
         */
        typedef string[10] tenStrings;
        typedef sequence<string> stringSeq;
        typedef sequence< sequence<string> > stringSeqSeq;

        interface QoSAdmin {
            stringSeq method1( in string arg1, inout long arg2 );
            stringSeqSeq method2( in string arg1, inout long arg2, inout long arg3);
            string method3();
          };
        """
    )
    test(
        """
        /*
         * a block comment *
         */
        typedef string[10] tenStrings;
        typedef
            /** ** *** **** *
             * a block comment *
             */
            sequence<string> /*comment inside an And */ stringSeq;
        /* */  /**/ /***/ /****/
        typedef sequence< sequence<string> > stringSeqSeq;

        interface QoSAdmin {
            stringSeq method1( in string arg1, inout long arg2 );
            stringSeqSeq method2( in string arg1, inout long arg2, inout long arg3);
            string method3();
          };
        """
    )
    test(
        r"""
          const string test="Test String\n";
          const long  a = 0;
          const long  b = -100;
          const float c = 3.14159;
          const long  d = 0x007f7f7f;
          exception TestException
            {
            string msg;
            sequence<string> dataStrings;
            };

          interface TestInterface
            {
            void method1( in string arg1, inout long arg2 );
            };
        """
    )
    test(
        """
        module Test1
          {
          exception TestException
            {
            string msg;
            ];

          interface TestInterface
            {
            void method1( in string arg1, inout long arg2 )
              raises ( TestException );
            };
          };
        """
    )
    test(
        """
        module Test1
          {
          exception TestException
            {
            string msg;
            };

          };
        """
    )
