from full_parse import *

def test_all():
    # Test aliases and defaults
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
