#!/usr/bin/python

# sql2dot.py
#
#  Creates table graphics by parsing SQL table DML commands and
#  generating DOT language output.
#
#  Adapted from a post at https://energyblog.blogspot.com/2006/04/blog-post_20.html.
#
sampleSQL = """
create table students
(
student_id integer primary key,
firstname varchar(20),
lastname varchar(40),
address1 varchar(80),
address2 varchar(80),
city varchar(30),
state varchar(2),
zipcode varchar(10),
dob date
);

create table classes
(
class_id integer primary key,
id varchar(8),
maxsize integer,
instructor varchar(40)
);

create table student_registrations
(
reg_id integer primary key,
student_id integer,
class_id integer
);

alter table only student_registrations
    add constraint students_link
    foreign key
    (student_id) references students(student_id);

alter table only student_registrations
    add constraint classes_link
    foreign key
    (class_id) references classes(class_id);
""".upper()

from pyparsing import (
    Literal,
    Word,
    DelimitedList,
    alphas,
    alphanums,
    OneOrMore,
    ZeroOrMore,
    CharsNotIn,
    replace_with,
)

skobki = "(" + ZeroOrMore(CharsNotIn(")")) + ")"
field_def = OneOrMore(Word(alphas, alphanums + "_\"':-") | skobki)


def field_act(s, loc, tok):
    return ("<" + tok[0] + "> " + " ".join(tok)).replace('"', '\\"')


field_def.set_parse_action(field_act)

field_list_def = DelimitedList(field_def)


def field_list_act(toks):
    return " | ".join(toks)


field_list_def.set_parse_action(field_list_act)

create_table_def = (
    Literal("CREATE")
    + "TABLE"
    + Word(alphas, alphanums + "_").set_results_name("tablename")
    + "("
    + field_list_def.set_results_name("columns")
    + ")"
    + ";"
)


def create_table_act(toks):
    return (
        """"%(tablename)s" [\n\t label="<%(tablename)s> %(tablename)s | %(columns)s"\n\t shape="record"\n];"""
        % toks
    )


create_table_def.set_parse_action(create_table_act)

add_fkey_def = (
    Literal("ALTER")
    + "TABLE"
    + "ONLY"
    + Word(alphanums + "_").set_results_name("fromtable")
    + "ADD"
    + "CONSTRAINT"
    + Word(alphanums + "_")
    + "FOREIGN"
    + "KEY"
    + "("
    + Word(alphanums + "_").set_results_name("fromcolumn")
    + ")"
    + "REFERENCES"
    + Word(alphanums + "_").set_results_name("totable")
    + "("
    + Word(alphanums + "_").set_results_name("tocolumn")
    + ")"
    + ";"
)


def add_fkey_act(toks):
    return """ "%(fromtable)s":%(fromcolumn)s -> "%(totable)s":%(tocolumn)s """ % toks


add_fkey_def.set_parse_action(add_fkey_act)

other_statement_def = OneOrMore(CharsNotIn(";")) + ";"
other_statement_def.set_parse_action(replace_with(""))
comment_def = "--" + ZeroOrMore(CharsNotIn("\n"))
comment_def.set_parse_action(replace_with(""))

statement_def = comment_def | create_table_def | add_fkey_def | other_statement_def
defs = OneOrMore(statement_def)

print("""digraph g { graph [ rankdir = "LR" ]; """)
for i in defs.parse_string(sampleSQL):
    if i != "":
        print(i)
print("}")
