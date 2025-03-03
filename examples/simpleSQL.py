# simpleSQL.py
#
# simple demo of using the parsing library to do simple-minded SQL parsing
# could be extended to include where clauses etc.
#
# Copyright (c) 2003,2016, Paul McGuire
#
from pyparsing import (
    Word,
    DelimitedList,
    Optional,
    Group,
    alphas,
    alphanums,
    Forward,
    one_of,
    quoted_string,
    infix_notation,
    OpAssoc,
    rest_of_line,
    CaselessKeyword,
    ParserElement,
    pyparsing_common as ppc,
)

ParserElement.enable_packrat()

# define SQL tokens
selectStmt = Forward()
SELECT, FROM, WHERE, AND, OR, IN, IS, NOT, NULL = map(
    CaselessKeyword, "select from where and or in is not null".split()
)
NOT_NULL = NOT + NULL

ident = Word(alphas, alphanums + "_$").set_name("identifier")
columnName = DelimitedList(ident, ".", combine=True).set_name("column name")
columnName.add_parse_action(ppc.upcase_tokens)
columnNameList = Group(DelimitedList(columnName).set_name("column_list"))
tableName = DelimitedList(ident, ".", combine=True).set_name("table name")
tableName.add_parse_action(ppc.upcase_tokens)
tableNameList = Group(DelimitedList(tableName).set_name("table_list"))

binop = one_of("= != < > >= <= eq ne lt le gt ge", caseless=True).set_name("binop")
realNum = ppc.real().set_name("real number")
intNum = ppc.signed_integer()

columnRval = (
    realNum | intNum | quoted_string | columnName
).set_name("column_rvalue")  # need to add support for alg expressions
whereCondition = Group(
    (columnName + binop + columnRval)
    | (columnName + IN + Group("(" + DelimitedList(columnRval).set_name("in_values_list") + ")"))
    | (columnName + IN + Group("(" + selectStmt + ")"))
    | (columnName + IS + (NULL | NOT_NULL))
).set_name("where_condition")

whereExpression = infix_notation(
    whereCondition,
    [
        (NOT, 1, OpAssoc.RIGHT),
        (AND, 2, OpAssoc.LEFT),
        (OR, 2, OpAssoc.LEFT),
    ],
).set_name("where_expression")

# define the grammar
selectStmt <<= (
    SELECT
    + ("*" | columnNameList)("columns")
    + FROM
    + tableNameList("tables")
    + Optional(Group(WHERE + whereExpression), "")("where")
).set_name("select_statement")

simpleSQL = selectStmt

# define Oracle comment format, and ignore them
oracleSqlComment = "--" + rest_of_line
simpleSQL.ignore(oracleSqlComment)

if __name__ == "__main__":
    simpleSQL.run_tests(
        """\

        # multiple tables
        SELECT * from XYZZY, ABC

        # dotted table name
        select * from SYS.XYZZY

        Select A from Sys.dual

        Select A,B,C from Sys.dual

        Select A, B, C from Sys.dual, Table2

        # FAIL - invalid SELECT keyword
        Xelect A, B, C from Sys.dual

        # FAIL - invalid FROM keyword
        Select A, B, C frox Sys.dual

        # FAIL - incomplete statement
        Select

        # FAIL - incomplete statement
        Select * from

        # FAIL - invalid column
        Select &&& frox Sys.dual

        # where clause
        Select A from Sys.dual where a in ('RED','GREEN','BLUE')

        # compound where clause
        Select A from Sys.dual where a in ('RED','GREEN','BLUE') and b in (10,20,30)

        # where clause with comparison operator
        Select A,b from table1,table2 where table1.id eq table2.id
        """
    )
