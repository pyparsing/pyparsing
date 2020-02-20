#
# configparse.py
#
# an example of using the parsing module to be able to process a .INI configuration file
#
# Copyright (c) 2003, Paul McGuire
#
import pprint

from examples.configParse import inifile_BNF

pp = pprint.PrettyPrinter(2)


def test(strng):
    print(strng)
    iniFile = open(strng)
    iniData = "".join(iniFile.readlines())
    bnf = inifile_BNF()
    tokens = bnf.parseString(iniData)
    pp.pprint(tokens.asList())

    iniFile.close()
    print()
    return tokens


ini = test("examples/setup.ini")
print("ini['Startup']['modemid'] =", ini["Startup"]["modemid"])
print("ini.Startup =", ini.Startup)
print("ini.Startup.modemid =", ini.Startup.modemid)
