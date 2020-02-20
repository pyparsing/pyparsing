import sys

from examples.LAparser import (
    exprStack,
    _evaluateStack,
    UnaryUnsupportedError,
    debug_flag,
    targetvar,
    _assignfunc,
    equation,
)


def test():
    """
   Tests the parsing of various supported expressions. Raises
   an AssertError if the output is not what is expected. Prints the
   input, expected output, and actual output for all tests.
   """
    print("Testing LAParser")
    testcases = [
        ("Scalar addition", "a = b+c", "a=(b+c)"),
        ("Vector addition", "V3_a = V3_b + V3_c", "vCopy(a,vAdd(b,c))"),
        ("Vector addition", "V3_a=V3_b+V3_c", "vCopy(a,vAdd(b,c))"),
        ("Matrix addition", "M3_a = M3_b + M3_c", "mCopy(a,mAdd(b,c))"),
        ("Matrix addition", "M3_a=M3_b+M3_c", "mCopy(a,mAdd(b,c))"),
        ("Scalar subtraction", "a = b-c", "a=(b-c)"),
        ("Vector subtraction", "V3_a = V3_b - V3_c", "vCopy(a,vSubtract(b,c))"),
        ("Matrix subtraction", "M3_a = M3_b - M3_c", "mCopy(a,mSubtract(b,c))"),
        ("Scalar multiplication", "a = b*c", "a=b*c"),
        ("Scalar division", "a = b/c", "a=b/c"),
        ("Vector multiplication (dot product)", "a = V3_b * V3_c", "a=vDot(b,c)"),
        (
            "Vector multiplication (outer product)",
            "M3_a = V3_b @ V3_c",
            "mCopy(a,vOuterProduct(b,c))",
        ),
        ("Matrix multiplication", "M3_a = M3_b * M3_c", "mCopy(a,mMultiply(b,c))"),
        ("Vector scaling", "V3_a = V3_b * c", "vCopy(a,vScale(b,c))"),
        ("Matrix scaling", "M3_a = M3_b * c", "mCopy(a,mScale(b,c))"),
        (
            "Matrix by vector multiplication",
            "V3_a = M3_b * V3_c",
            "vCopy(a,mvMultiply(b,c))",
        ),
        ("Scalar exponentiation", "a = b^c", "a=pow(b,c)"),
        ("Matrix inversion", "M3_a = M3_b^-1", "mCopy(a,mInverse(b))"),
        ("Matrix transpose", "M3_a = M3_b^T", "mCopy(a,mTranspose(b))"),
        ("Matrix determinant", "a = M3_b^Det", "a=mDeterminant(b)"),
        ("Vector magnitude squared", "a = V3_b^Mag2", "a=vMagnitude2(b)"),
        ("Vector magnitude", "a = V3_b^Mag", "a=sqrt(vMagnitude2(b))"),
        (
            "Complicated expression",
            "myscalar = (M3_amatrix * V3_bvector)^Mag + 5*(-xyz[i] + 2.03^2)",
            "myscalar=(sqrt(vMagnitude2(mvMultiply(amatrix,bvector)))+5*(-xyz[i]+pow(2.03,2)))",
        ),
        (
            "Complicated Multiline",
            "myscalar = \n(M3_amatrix * V3_bvector)^Mag +\n 5*(xyz + 2.03^2)",
            "myscalar=(sqrt(vMagnitude2(mvMultiply(amatrix,bvector)))+5*(xyz+pow(2.03,2)))",
        ),
    ]

    all_passed = [True]

    def post_test(test, parsed):

        # copy exprStack to evaluate and clear before running next test
        parsed_stack = exprStack[:]
        exprStack.clear()

        name, testcase, expected = next(tc for tc in testcases if tc[1] == test)

        this_test_passed = False
        try:
            try:
                result = _evaluateStack(parsed_stack)
            except TypeError:
                print(
                    "Unsupported operation on right side of '%s'.\nCheck for missing or incorrect tags on non-scalar operands."
                    % input_string,
                    file=sys.stderr,
                )
                raise
            except UnaryUnsupportedError:
                print(
                    "Unary negation is not supported for vectors and matrices: '%s'"
                    % input_string,
                    file=sys.stderr,
                )
                raise

            # Create final assignment and print it.
            if debug_flag:
                print("var=", targetvar)
            if targetvar != None:
                try:
                    result = _assignfunc(targetvar, result)
                except TypeError:
                    print(
                        "Left side tag does not match right side of '%s'"
                        % input_string,
                        file=sys.stderr,
                    )
                    raise
                except UnaryUnsupportedError:
                    print(
                        "Unary negation is not supported for vectors and matrices: '%s'"
                        % input_string,
                        file=sys.stderr,
                    )
                    raise

            else:
                print("Empty left side in '%s'" % input_string, file=sys.stderr)
                raise TypeError

            parsed["result"] = result
            parsed["passed"] = this_test_passed = result == expected

        finally:
            all_passed[0] = all_passed[0] and this_test_passed
            print("\n" + name)

    equation.runTests((t[1] for t in testcases), postParse=post_test)

    ##TODO: Write testcases with invalid expressions and test that the expected
    ## exceptions are raised.

    print("Tests completed!")
    print("PASSED" if all_passed[0] else "FAILED")
    assert all_passed[0]
