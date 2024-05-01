from full_parse import *

def test_all():    
    # Test aliases and defaults  
    parser = Parser() 
    parser.arg_aliases = {">": "sus"}
    parser.arg_defaults = {"sus": Decimal("1.0")}
    res = parser.parse("0:>0.5")
    assert res[0].args["sus"] == Decimal("0.5"), res[0].args
