# simpleSQL.py
#
# simple demo of using the parsing library to do simple-minded SQL parsing
# could be extended to include where clauses etc.
#
# Copyright (c) 2003,2016, Paul McGuire
#
from pyparsing import (
    Word,
    delimitedList,
    Optional,
    Group,
    alphas,
    alphanums,
    Forward,
    oneOf,
    quotedString,
    infixNotation,
    opAssoc,
    restOfLine,
    CaselessKeyword,
    pyparsing_common as ppc,
)

# define SQL tokens
selectStmt = Forward()
SELECT, FROM, WHERE, AND, OR, IN, IS, NOT, NULL = map(
    CaselessKeyword, "select from where and or in is not null".split()
)
NOT_NULL = NOT + NULL

ident = Word(alphas, alphanums + "_$").setName("identifier")
columnName = delimitedList(ident, ".", combine=True).setName("column name")
columnName.addParseAction(ppc.upcaseTokens)
columnNameList = Group(delimitedList(columnName))
tableName = delimitedList(ident, ".", combine=True).setName("table name")
tableName.addParseAction(ppc.upcaseTokens)
tableNameList = Group(delimitedList(tableName))

binop = oneOf("= != < > >= <= eq ne lt le gt ge", caseless=True)
realNum = ppc.real()
intNum = ppc.signed_integer()

columnRval = (
    realNum | intNum | quotedString | columnName
)  # need to add support for alg expressions
whereCondition = Group(
    (columnName + binop + columnRval)
    | (columnName + IN + Group("(" + delimitedList(columnRval) + ")"))
    | (columnName + IN + Group("(" + selectStmt + ")"))
    | (columnName + IS + (NULL | NOT_NULL))
)

whereExpression = infixNotation(
    whereCondition,
    [(NOT, 1, opAssoc.RIGHT), (AND, 2, opAssoc.LEFT), (OR, 2, opAssoc.LEFT)],
)

# define the grammar
selectStmt <<= (
    SELECT
    + ("*" | columnNameList)("columns")
    + FROM
    + tableNameList("tables")
    + Optional(Group(WHERE + whereExpression), "")("where")
)

simpleSQL = selectStmt

# define Oracle comment format, and ignore them
oracleSqlComment = "--" + restOfLine
simpleSQL.ignore(oracleSqlComment)
