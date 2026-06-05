from full_parse import *

def test_aliases_and_defaults():
    parser = Parser()
    parser.arg_aliases = {">": "sus"}
    parser.arg_defaults = {"sus": Decimal("1.0")}
    res = parser.parse("0:>0.5")
    assert res[0].args["sus"] == Decimal("0.5"), res[0].args

    parser.arg_defaults = {"time": Decimal("1.0")}
    res = parser.parse("a4*3 (d4 / g4)")
    assert res[0].args["time"] == Decimal("1.0")

    res = parser.parse("(c4:sus*0.5):2.0,sus1time")
    assert res[0].args["sus"] == Decimal("1.0"), "sus failed"


def test_nested_arg_override_inner_wins():
    """Inner element arg overrides outer section arg."""
    parser = Parser()
    res = parser.parse("(a:lol4.0):lol3.0")
    assert res[0].args["lol"] == Decimal("4.0"), f"got {res[0].args['lol']}"


def test_nested_arg_operator_applies_to_parent():
    """Inner element adds to outer section arg via operator."""
    parser = Parser()
    res = parser.parse("(a:lol+1.0):lol3.0")
    assert res[0].args["lol"] == Decimal("4.0"), f"got {res[0].args['lol']}"


def test_deeply_nested_arg_innermost_wins():
    """Across three levels, innermost override wins."""
    parser = Parser()
    res = parser.parse("((a:lol4.0):lol3.0):lol2.0")
    assert res[0].args["lol"] == Decimal("4.0"), f"got {res[0].args['lol']}"


def test_section_arg_cascades_to_children():
    """Section arg applies to elements that don't override it."""
    parser = Parser()
    res = parser.parse("(c4 d4):dur0.8")
    assert res[0].args["dur"] == Decimal("0.8"), f"got {res[0].args['dur']}"
    assert res[1].args["dur"] == Decimal("0.8"), f"got {res[1].args['dur']}"


def test_element_override_keeps_other_section_args():
    """Element overrides one arg but inherits another from section."""
    parser = Parser()
    res = parser.parse("(c4:dur0.5,vel1.0):dur0.8")
    assert res[0].args["dur"] == Decimal("0.5"), f"got {res[0].args['dur']}"
    assert res[0].args["vel"] == Decimal("1.0"), f"got {res[0].args['vel']}"


def test_section_base_child_multiplies():
    """Section provides base value, child multiplies it with * operator."""
    parser = Parser()
    res = parser.parse("(c4:time*2):time3.0")
    assert res[0].args["time"] == Decimal("6.0"), f"got {res[0].args['time']}"


def test_section_base_child_adds():
    """Section provides base value, child adds with + operator."""
    parser = Parser()
    res = parser.parse("(c4:time+1.5):time3.0")
    assert res[0].args["time"] == Decimal("4.5"), f"got {res[0].args['time']}"


def test_section_base_child_negates():
    """Section provides base value, child's '-' multiplies (negate)."""
    parser = Parser()
    res = parser.parse("(c4:time-0.5):time3.0")
    # -= does *= in current impl: 3.0 * 0.5 = 1.5
    assert res[0].args["time"] == Decimal("1.5"), f"got {res[0].args['time']}"


def test_child_plain_value_overwrites_section_modifier():
    """Child with plain value (no operator) overwrites section's modifier."""
    parser = Parser()
    res = parser.parse("(a:2):*3.0")
    # Section provides time*3.0, but child has plain time=2 which overwrites
    assert res[0].args["time"] == Decimal("2.0"), f"got {res[0].args['time']}"


def test_operator_on_element_without_parent_is_flat():
    """* operator on element with no parent acts as flat value, not multiply."""
    parser = Parser()
    res = parser.parse("a:*3.0")
    assert res[0].args["time"] == Decimal("3.0"), f"got {res[0].args['time']}"



