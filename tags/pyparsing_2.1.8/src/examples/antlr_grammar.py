'''
antlr_grammar.py

Created on 4 sept. 2010

@author: luca

Submitted by Luca DallOlio, September, 2010
(Minor updates by Paul McGuire, June, 2012)
'''
from pyparsing import Word, ZeroOrMore, printables, Suppress, OneOrMore, Group, \
    LineEnd, Optional, White, originalTextFor, hexnums, nums, Combine, Literal, Keyword, \
    cStyleComment, Regex, Forward, MatchFirst, And, srange, oneOf, alphas, alphanums, \
    delimitedList

# http://www.antlr.org/grammar/ANTLR/ANTLRv3.g

# Tokens
EOL = Suppress(LineEnd()) # $
singleTextString = originalTextFor(ZeroOrMore(~EOL + (White(" \t") | Word(printables)))).leaveWhitespace()
XDIGIT = hexnums
INT = Word(nums)
ESC = Literal('\\') + (oneOf(list(r'nrtbf\">'+"'")) | ('u' + Word(hexnums, exact=4)) | Word(printables, exact=1))
LITERAL_CHAR = ESC | ~(Literal("'") | Literal('\\')) + Word(printables, exact=1)
CHAR_LITERAL = Suppress("'") + LITERAL_CHAR + Suppress("'")
STRING_LITERAL = Suppress("'") + Combine(OneOrMore(LITERAL_CHAR)) + Suppress("'") 
DOUBLE_QUOTE_STRING_LITERAL = '"' + ZeroOrMore(LITERAL_CHAR) + '"'
DOUBLE_ANGLE_STRING_LITERAL = '<<' + ZeroOrMore(Word(printables, exact=1)) + '>>'
TOKEN_REF = Word(alphas.upper(), alphanums+'_')
RULE_REF = Word(alphas.lower(), alphanums+'_')
ACTION_ESC = (Suppress("\\") + Suppress("'")) | Suppress('\\"') | Suppress('\\') + (~(Literal("'") | Literal('"')) + Word(printables, exact=1))
ACTION_CHAR_LITERAL = Suppress("'") + (ACTION_ESC | ~(Literal('\\') | Literal("'")) + Word(printables, exact=1)) + Suppress("'")
ACTION_STRING_LITERAL = Suppress('"') + ZeroOrMore(ACTION_ESC | ~(Literal('\\') | Literal('"')) + Word(printables, exact=1)) + Suppress('"') 
SRC = Suppress('src') + ACTION_STRING_LITERAL("file") + INT("line")
id = TOKEN_REF | RULE_REF
SL_COMMENT = Suppress('//') + Suppress('$ANTLR') + SRC | ZeroOrMore(~EOL + Word(printables)) + EOL
ML_COMMENT = cStyleComment
WS = OneOrMore(Suppress(' ') | Suppress('\t') | (Optional(Suppress('\r')) + Literal('\n')))
WS_LOOP = ZeroOrMore(SL_COMMENT | ML_COMMENT)
NESTED_ARG_ACTION = Forward()
NESTED_ARG_ACTION << Suppress('[') + ZeroOrMore(NESTED_ARG_ACTION | ACTION_STRING_LITERAL | ACTION_CHAR_LITERAL) + Suppress(']')
ARG_ACTION = NESTED_ARG_ACTION
NESTED_ACTION = Forward()
NESTED_ACTION << Suppress('{') + ZeroOrMore(NESTED_ACTION | SL_COMMENT | ML_COMMENT | ACTION_STRING_LITERAL | ACTION_CHAR_LITERAL) + Suppress('}')
ACTION = NESTED_ACTION + Optional('?')
SCOPE = Suppress('scope')
OPTIONS = Suppress('options') + Suppress('{') # + WS_LOOP + Suppress('{')
TOKENS = Suppress('tokens') + Suppress('{') # + WS_LOOP + Suppress('{')
FRAGMENT = 'fragment';
TREE_BEGIN = Suppress('^(')
ROOT = Suppress('^')
BANG = Suppress('!')
RANGE = Suppress('..')
REWRITE = Suppress('->')

# General Parser Definitions

# Grammar heading
optionValue = id | STRING_LITERAL | CHAR_LITERAL | INT | Literal('*').setName("s")

option = Group(id("id") + Suppress('=') + optionValue("value"))("option")
optionsSpec = OPTIONS + Group(OneOrMore(option + Suppress(';')))("options") + Suppress('}')
tokenSpec = Group(TOKEN_REF("token_ref") + (Suppress('=') + (STRING_LITERAL | CHAR_LITERAL)("lit")))("token") + Suppress(';')
tokensSpec = TOKENS + Group(OneOrMore(tokenSpec))("tokens") + Suppress('}')
attrScope = Suppress('scope') + id + ACTION
grammarType = Keyword('lexer') + Keyword('parser') + Keyword('tree')
actionScopeName = id | Keyword('lexer')("l") | Keyword('parser')("p")
action = Suppress('@') + Optional(actionScopeName + Suppress('::')) + id + ACTION

grammarHeading = Optional(ML_COMMENT("ML_COMMENT")) + Optional(grammarType) + Suppress('grammar') + id("grammarName") + Suppress(';') + Optional(optionsSpec) + Optional(tokensSpec) + ZeroOrMore(attrScope) + ZeroOrMore(action)

modifier = Keyword('protected') | Keyword('public') | Keyword('private') | Keyword('fragment')
ruleAction = Suppress('@') + id + ACTION
throwsSpec = Suppress('throws') + delimitedList(id)
ruleScopeSpec = (Suppress('scope') + ACTION) | (Suppress('scope') + delimitedList(id) + Suppress(';')) | (Suppress('scope') + ACTION + Suppress('scope') + delimitedList(id) + Suppress(';'))
unary_op = oneOf("^ !")
notTerminal = CHAR_LITERAL | TOKEN_REF | STRING_LITERAL
terminal = (CHAR_LITERAL | TOKEN_REF + Optional(ARG_ACTION) | STRING_LITERAL | '.') + Optional(unary_op)
block = Forward()
notSet = Suppress('~') + (notTerminal | block)
rangeNotPython = CHAR_LITERAL("c1") + RANGE + CHAR_LITERAL("c2")
atom = Group(rangeNotPython + Optional(unary_op)("op")) | terminal | (notSet + Optional(unary_op)("op")) | (RULE_REF + Optional(ARG_ACTION("arg")) + Optional(unary_op)("op"))
element = Forward()
treeSpec = Suppress('^(') + element*(2,) + Suppress(')')
ebnfSuffix = oneOf("? * +")
ebnf = block + Optional(ebnfSuffix("op") | '=>')
elementNoOptionSpec = (id("result_name") + oneOf('= +=')("labelOp") + atom("atom") + Optional(ebnfSuffix)) | (id("result_name") + oneOf('= +=')("labelOp") + block + Optional(ebnfSuffix)) | atom("atom") + Optional(ebnfSuffix) | ebnf | ACTION | (treeSpec + Optional(ebnfSuffix)) # |   SEMPRED ( '=>' -> GATED_SEMPRED | -> SEMPRED )
element << Group(elementNoOptionSpec)("element")
alternative = Group(Group(OneOrMore(element))("elements")) # Do not ask me why group is needed twice... seems like the xml that you see is not always the real structure?
rewrite = Optional(Literal('TODO REWRITE RULES TODO'))
block << Suppress('(') + Optional(Optional(optionsSpec("opts")) + Suppress(':')) + Group(alternative('a1') + rewrite + Group(ZeroOrMore(Suppress('|') + alternative('a2') + rewrite))("alternatives"))("block") + Suppress(')')
altList = alternative('a1') + rewrite + Group(ZeroOrMore(Suppress('|') + alternative('a2') + rewrite))("alternatives")
exceptionHandler = Suppress('catch') + ARG_ACTION + ACTION
finallyClause = Suppress('finally') + ACTION 
exceptionGroup = (OneOrMore(exceptionHandler) + Optional(finallyClause)) | finallyClause

ruleHeading = Optional(ML_COMMENT)("ruleComment") + Optional(modifier)("modifier") + id("ruleName") + Optional("!") + Optional(ARG_ACTION("arg")) + Optional(Suppress('returns') + ARG_ACTION("rt")) + Optional(throwsSpec) + Optional(optionsSpec) + Optional(ruleScopeSpec) + ZeroOrMore(ruleAction)
rule = Group(ruleHeading + Suppress(':') + altList + Suppress(';') + Optional(exceptionGroup))("rule")

grammarDef = grammarHeading + Group(OneOrMore(rule))("rules")

def grammar():
    return grammarDef

def __antlrAlternativesConverter(pyparsingRules, antlrBlock):
    rule = None
    if hasattr(antlrBlock, 'alternatives') and antlrBlock.alternatives != '' and len(antlrBlock.alternatives) > 0:
        alternatives = []
        alternatives.append(__antlrAlternativeConverter(pyparsingRules, antlrBlock.a1))
        for alternative in antlrBlock.alternatives:
            alternatives.append(__antlrAlternativeConverter(pyparsingRules, alternative))
        rule = MatchFirst(alternatives)("anonymous_or")
    elif hasattr(antlrBlock, 'a1') and antlrBlock.a1 != '':
        rule = __antlrAlternativeConverter(pyparsingRules, antlrBlock.a1)
    else:
        raise Exception('Not yet implemented')
    assert rule != None
    return rule

def __antlrAlternativeConverter(pyparsingRules, antlrAlternative):
    elementList = []
    for element in antlrAlternative.elements:
        rule = None
        if hasattr(element.atom, 'c1') and element.atom.c1 != '':
            regex = r'['+str(element.atom.c1[0])+'-'+str(element.atom.c2[0]+']')
            rule = Regex(regex)("anonymous_regex")
        elif hasattr(element, 'block') and element.block != '':
            rule = __antlrAlternativesConverter(pyparsingRules, element.block)        
        else:
            ruleRef = element.atom
            assert ruleRef in pyparsingRules
            rule = pyparsingRules[element.atom](element.atom)
        if hasattr(element, 'op') and element.op != '':
            if element.op == '+':
                rule = Group(OneOrMore(rule))("anonymous_one_or_more")
            elif element.op == '*':
                rule = Group(ZeroOrMore(rule))("anonymous_zero_or_more")
            elif element.op == '?':
                rule = Optional(rule)
            else:
                raise Exception('rule operator not yet implemented : ' + element.op)
        rule = rule
        elementList.append(rule)
    if len(elementList) > 1:
        rule = Group(And(elementList))("anonymous_and")
    else:
        rule = elementList[0]
    assert rule != None        
    return rule

def __antlrRuleConverter(pyparsingRules, antlrRule):
    rule = None
    rule = __antlrAlternativesConverter(pyparsingRules, antlrRule)
    assert rule != None
    rule(antlrRule.ruleName)
    return rule

def antlrConverter(antlrGrammarTree):
    pyparsingRules = {}
    antlrTokens = {}
    for antlrToken in antlrGrammarTree.tokens:
        antlrTokens[antlrToken.token_ref] = antlrToken.lit
    for antlrTokenName, antlrToken in list(antlrTokens.items()):
        pyparsingRules[antlrTokenName] = Literal(antlrToken)
    antlrRules = {}
    for antlrRule in antlrGrammarTree.rules:
        antlrRules[antlrRule.ruleName] = antlrRule
        pyparsingRules[antlrRule.ruleName] = Forward() # antlr is a top down grammar
    for antlrRuleName, antlrRule in list(antlrRules.items()):
        pyparsingRule = __antlrRuleConverter(pyparsingRules, antlrRule)
        assert pyparsingRule != None
        pyparsingRules[antlrRuleName] << pyparsingRule 
    return pyparsingRules

if __name__ == "__main__":
    
    text = """grammar SimpleCalc;

options {
    language = Python;
}

tokens {
    PLUS     = '+' ;
    MINUS    = '-' ;
    MULT    = '*' ;
    DIV    = '/' ;
}

/*------------------------------------------------------------------
 * PARSER RULES
 *------------------------------------------------------------------*/

expr    : term ( ( PLUS | MINUS )  term )* ;

term    : factor ( ( MULT | DIV ) factor )* ;

factor    : NUMBER ;


/*------------------------------------------------------------------
 * LEXER RULES
 *------------------------------------------------------------------*/

NUMBER    : (DIGIT)+ ;

/* WHITESPACE : ( '\t' | ' ' | '\r' | '\n'| '\u000C' )+     { $channel = HIDDEN; } ; */

fragment DIGIT    : '0'..'9' ;

"""
    
    grammar().validate()
    antlrGrammarTree = grammar().parseString(text)
    print(antlrGrammarTree.asXML("antlrGrammarTree"))
    pyparsingRules = antlrConverter(antlrGrammarTree)
    pyparsingRule = pyparsingRules["expr"]
    pyparsingTree = pyparsingRule.parseString("2 - 5 * 42 + 7 / 25")
    print(pyparsingTree.asXML("pyparsingTree"))
