import pytest 
from util import *

# TODO: Split into proper tests 
def test_all():
    assert section_split("a b c") == ["a", "b", "c"]
    assert section_split("a (f) c") == ["a", "(f)", "c"]
    assert section_split("a (f (b a ()) / tt) c") == ["a", "(f (b a ()) / tt)", "c"]

    tree = TreeExpander()

    # Quick assertion of atomic elements after a full tree alternations expand    
    # Mixing in some parse logic for faster testing ...     
    def assert_expanded(parse_source, expect):
        top_element = section_parsing.build_tree(parse_source)
        tree_expand_string = " ".join([e.information for e in tree.tree_expand(top_element)])
        assert tree_expand_string == expect, tree_expand_string

    assert_expanded("1 (2 / (3 4 / (5 / 6)))", "1 2 1 3 4 1 2 1 5 1 2 1 3 4 1 2 1 6")

    # Repeat testing
    assert_expanded("2*3", "2*3 2*3 2*3")
    assert_expanded("(1 2)*2", "1 2 1 2")
    assert_expanded("t / (a / b)", "t a t b")
    assert_expanded("2*3 / (a / b)", "2*3 2*3 2*3 a 2*3 2*3 2*3 b")    
    assert_expanded("t / (a / b)*3", "t a b a t b a b")
    assert_expanded("t / (f ((a / b)))*2", "t f a f b t f a f b")
    assert_expanded("0*3 (1 / 2)", "0*3 0*3 0*3 1 0*3 0*3 0*3 2")

    assert_expanded("a (b / c / d)*3", "a b c d")

    # Arg resolution testing

    ### Verify history logic 
    grandparent = section_parsing.build_tree("((0a)b)c")
    child = grandparent.elements[0].elements[0].elements[0]
    h1 = [i.suffix for i in get_information_history(child)]
    assert h1 == ["a", "b", "c", ""], h1

    # Fake an information history using bastardized parsing 
    def build_arg_array(source):
        elements = section_parsing.build_tree(source).elements
        return [information_parsing.divide_information(e) for e in elements]

    def arg_tree_test(array_source, expected_dict, defaults = {}, aliases = {}):
        history = build_arg_array(array_source)
        args = resolve_full_arguments(history, defaults, aliases)

        for key in expected_dict:
            assert args[key] == expected_dict[key], args[key]

    arg_tree_test("a3:aa0.2,ab+0.2,ac-0.2", {
        "aa": Decimal("0.2"),
        "ab": Decimal("0.2"),
        "ac": Decimal("0.2")
    })

    arg_tree_test("0:a+0.1 0:a+0.1 0:a+0.1", {
            "a": Decimal("0.3")
    })
        
    arg_tree_test("0:a+0.1 0:a*0.5 0:a2.0", {
            "a": Decimal("1.1")
    })
    
    arg_tree_test("0:a0.2 0:a*44 0:a1", {
            "a": Decimal("0.2")
    })    

    # Simple default
    arg_tree_test("0", {
            "sus": Decimal("1.0")
    }, {"sus": Decimal("1.0")})


    # Simple alias
    arg_tree_test("0:>1.0", {
            "sus": Decimal("1.0")
    }, aliases={">": "sus"})

    # Aliased default
    arg_tree_test("0:>1.0", {
            "sus": Decimal("1.0")
    }, defaults={"sus": Decimal("2.0")}, aliases={">": "sus"})
