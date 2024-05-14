import pytest
from information_parsing import *

# TODO: Split into proper tests 
def test_all():

    # Args tests 

    no_arg_test = parse_args("")
    assert len(no_arg_test) == 0

    arg_test_basic = parse_args("1.0")
    assert arg_test_basic["time"].value == Decimal("1.0"), arg_test_basic["time"].value
    assert len(arg_test_basic) == 1, len(arg_test_basic)

    arg_test_basic_2 = parse_args("fish1.0,cheese0.3")
    assert "fish" in arg_test_basic_2
    assert "cheese" in arg_test_basic_2
    assert arg_test_basic_2["fish"].value == Decimal("1.0"), arg_test_basic_2["fish"].value
    assert arg_test_basic_2["cheese"].value == Decimal("0.3"), arg_test_basic_2["cheese"].value
    
    arg_test = parse_args("0.2,;900,lob0.002")
    assert "time" in arg_test
    assert ";" in arg_test
    assert "lob" in arg_test
    assert arg_test["time"].value == Decimal("0.2"), arg_test["time"].value
    assert arg_test[";"].value == Decimal("900"), arg_test[";"].value
    assert arg_test["lob"].value == Decimal("0.002"), arg_test["lob"].value

    symtest = parse_args("a+4,b*0.2,c-1.2,d0.3")
    assert symtest["a"].operator == "+", symtest["a"].operator
    assert symtest["b"].operator == "*", symtest["b"].operator
    assert symtest["c"].operator == "-", symtest["c"].operator
    assert symtest["d"].operator == "", symtest["d"].operator


    # Divide information testing

    def make_element(source, etype):
        ele = Element() 
        ele.information = source
        ele.type = etype
        return ele 

    def divide_test(source, prefix, index, suffix, repeat, args):
        divtest = divide_information(make_element(source, ElementType.ATOMIC))
        assert divtest.prefix == prefix, divtest.prefix
        assert divtest.index_string == index, divtest.index_string
        assert divtest.suffix == suffix, divtest.suffix
        assert divtest.repetition == repeat, divtest.repetition
        assert divtest.arg_source == args, divtest.arg_source

    divide_test("a3x:0.1@", "a", "3", "x", 1, "0.1@")
    divide_test("1", "", "1", "", 1, "")
    divide_test("9099:arg1", "", "9099", "", 1, "arg1")
    divide_test("001xxx", "", "001", "xxx", 1, "")
    divide_test("", "", "", "", 1, "")
    divide_test("a", "", "", "a", 1, "")
    divide_test("prefix33suf*3:arg0.1,arf0.2", "prefix", "33", "suf", 3, "arg0.1,arf0.2")
    divide_test("x:16", "", "", "x", 1, "16")

    stest = divide_information(make_element(":fff", ElementType.SECTION))
    assert stest.prefix == ""
    assert stest.index_string == ""
    assert stest.suffix == ""
    assert stest.arg_source == "fff" 

    startest = divide_information(make_element(":ss*s", ElementType.SECTION))
    assert stest.suffix == ""

    with pytest.raises(Exception) as exc_info:   
        divide_information(make_element(":fff", ElementType.ATOMIC))
        assert "Malformed input" in exc_info.value
