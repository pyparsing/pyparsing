import textwrap

import pyparsing as pp

from examples.tiny.tiny_parser import parse_tiny
ppt = pp.testing


def _test_tiny_code(code: str):
    print()
    print(ppt.with_line_numbers(code))
    try:
        result = parse_tiny(code)
    except pp.ParseException as pe:
        print(pe.explain())
        raise
    else:
        print(result.dump())


#
# code examples taken from https://a7medayman6.github.io/Tiny-Compiler/Language-Description.html
#
def test_tiny_grammar():
    code = textwrap.dedent("""\
    int sum(int a, int b)
    {
        return a + b;
    }
    int main()
    {
        int val, counter;
        read val;
    
        counter := 0;
    
        repeat
            val := val - 1;
            write "Iteration number [";
            write counter;
            write "] the value of x = ";
            write val;
            write endl;
            counter := counter+1;
        until val = 1
    
        write endl;
    
        string s := "number of Iterations = ";
        write s; 
    
        counter := counter-1;
    
        write counter;
    
        /* complicated equation */    
        float z1 := 3*2*(2+1)/2-5.3;
        z1 := z1 + sum(a,y);
    
        if  z1 > 5 || z1 < counter && z1 = 1 
        then 
            write z1;
        elseif z1 < 5 
        then
            z1 := 5;
        else
            z1 := counter;
        end
    
        return 0;
    }
    """)
    _test_tiny_code(code)


def test_tiny_grammar_factorial():
    code = """\
    /* Sample program in Tiny language – computes factorial*/
    int main()
    {
        int x;
        read x; /*input an integer*/
        if x > 0 /*don’t compute if x <= 0 */
        then 
            int fact := 1;
            repeat
                fact := fact * x;
                x := x - 1;
            until x = 0    
            write fact; /*output factorial of x*/
        end
        return 0;
    }
    """
    _test_tiny_code(code)
