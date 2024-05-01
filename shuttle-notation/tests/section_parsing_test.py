import section_parsing
import pytest

def test_malformed_input():
    # This should be OK, even if gibberish 
    section_parsing.build_tree("                ")

    def test_malformed_input(inp):
        with pytest.raises(Exception) as exc_info:   
            section_parsing.build_tree(inp)
            assert "Malformed input" in exc_info.value

    test_malformed_input("(a c v")
    test_malformed_input("(((((/)))))")
    test_malformed_input("a / / b")

def test_build_and_decopile():

    def representation_test(source):
        res = section_parsing.build_tree(source).decompile()
        assert res == "(" + source + ")", res 

    representation_test("a / (b c)fff")
    representation_test("a / b / c / d")
    representation_test("a")
    representation_test("b (c / d / (e / f))")    
    representation_test("a ((b / f) / (c d)f)")

    # Some nested alternation wrappings are harder to predict 
    def reptest_advanced(source, expect):
        res = section_parsing.build_tree(source).decompile()
        assert res == expect, res 

    reptest_advanced("a (b / (p f / (d / h)))", "(a (b / ((p f) / (d / h))))")
    reptest_advanced("a (a (b / f) / (c d)f)", "(a ((a (b / f)) / (c d)f))")
    reptest_advanced("a b c / (a (b / b2)z c / d d) c", "((a b c) / (((a (b / b2)z c) / (d d)) c))")
    
def test_information_inheritence():
    nested_arg_set = section_parsing.build_tree("f (( ::a)b )c")
    assert len(nested_arg_set.elements) == 2
    a_node = nested_arg_set.elements[1].elements[0].elements[0]
    assert a_node.get_information_array_ordered() == ["::a", "b", "c", ""], \
        "was: " + ",".join([a for a in a_node.get_information_array_ordered()])
