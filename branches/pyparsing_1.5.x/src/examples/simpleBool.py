#
# simpleBool.py
#
# Example of defining a boolean logic parser using
# the operatorGrammar helper method in pyparsing.
#
# In this example, parse actions associated with each
# operator expression will "compile" the expression
# into BoolOperand subclass objects, which can then
# later be evaluated for their boolean value.
#
# Copyright 2006, by Paul McGuire
#

from pyparsing import *

class BoolOperand(object):
    def __init__(self,t):
        self.args = t[0][0::2]
    def __str__(self):
        sep = " %s " % self.reprsymbol
        return "(" + sep.join(map(str,self.args)) + ")"
    
class BoolAnd(BoolOperand):
    reprsymbol = '&'
    def __nonzero__(self):
        for a in self.args:
            if isinstance(a,basestring):
                v = eval(a)
            else:
                v = bool(a)
            if not v:
                return False
        return True

class BoolOr(BoolOperand):
    reprsymbol = '|'    
    def __nonzero__(self):
        for a in self.args:
            if isinstance(a,basestring):
                v = eval(a)
            else:
                v = bool(a)
            if v:
                return True
        return False

class BoolNot(BoolOperand):
    def __init__(self,t):
        self.arg = t[0][1]
    def __str__(self):
        return "~" + str(self.arg)
    def __nonzero__(self):
        if isinstance(self.arg,basestring):
            v = eval(self.arg)
        else:
            v = bool(self.arg)
        return not v

boolOperand = Word(alphas,max=1) | oneOf("True False")
boolExpr = operatorPrecedence( boolOperand,
    [
    ("not", 1, opAssoc.RIGHT, BoolNot),
    ("and", 2, opAssoc.LEFT,  BoolAnd),
    ("or",  2, opAssoc.LEFT,  BoolOr),
    ])
test = ["p and not q",
        "not not p",
        "not(p and q)",
        "q or not p and r",
        "q or not p or not r",
        "q or not (p and r)",
        "p or q or r",
        "p or q or r and False",
        "(p or q or r) and False",
        ]

p = True
q = False
r = True
print "p =", p
print "q =", q
print "r =", r
print
for t in test:
    res = boolExpr.parseString(t)[0]
    print t,'\n', res, '=', bool(res),'\n'
    
