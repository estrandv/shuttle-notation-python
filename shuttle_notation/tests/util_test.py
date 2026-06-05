import pytest
from decimal import Decimal
from shuttle_notation.parsing.tree_sitter_backend import TreeSitterBackend
from shuttle_notation.parsing.element import ElementType
import shuttle_notation.parsing.util as util
import shuttle_notation.parsing.information_parsing as information_parsing


@pytest.fixture(scope="session")
def backend():
    return TreeSitterBackend()


def test_tree_expansion(backend):
    tree = util.TreeExpander()

    chunk = """
        2*3 => 2*3 2*3 2*3
        (1 2 3 4)*2 => 1 2 3 4 1 2 3 4
        (t (a / b))*2 => t a b t a b
        (f / (a / b)) => f a b
        1 (2 / (3 4 / (5 / 6))) => 1 2 3 4 5 6
        (2*3 / (a / b)) => 2*3 2*3 2*3 a b
        (t / (a / b)*3) => t a b a b a b
        (t / (f (a / b))) => t f a b
        (t / (f (a / b))*2) => t f a b f a b
        (f (g / a)) => f g a
        (0*3 (1 / 2)) => 0*3 0*3 0*3 1 2
        a (b / c / d)*3 => a b c d b c d b c d
        (a (b / c))*2 (f)*4 => a b c a b c f f f f
    """

    for line in chunk.split("\n"):
        pure = line.strip()
        if pure != "" and " => " in pure:
            arrow_split = pure.split(" => ")
            parse = arrow_split[0]
            expected = arrow_split[1]
            top_element = backend.parse(parse)
            result = " ".join([e.information for e in tree.tree_expand(top_element)])
            assert result == expected, f"{parse!r}: got {result!r} expected {expected!r}"


def test_information_history_nested(backend):
    top = backend.parse("((0a)b)c")
    # top: SECTION('c') → SECTION('b') → ATOMIC('0a')
    child = top.elements[0].elements[0]
    h1 = [i.suffix for i in util.get_information_history(child)]
    assert h1 == ["a", "b", "c"], h1


def test_information_history_alternation(backend):
    top = backend.parse("(3 (0a / 1) 4)c")
    # top: SECTION('c') → [ATOMIC('3'), SECTION('') → [ALTERNATION → [ATOMIC('0a'), ...]], ATOMIC('4')]
    child = top.elements[1].elements[0].elements[0]
    h1 = [i.suffix for i in util.get_information_history(child)]
    assert h1 == ["a", "", "", "c"], h1


def build_arg_array(backend, source):
    top = backend.parse(source)
    if top.type == ElementType.ATOMIC:
        return [top]
    return top.elements


def arg_tree_test(backend, array_source, expected_dict, defaults={}, aliases={}):
    elements = build_arg_array(backend, array_source)
    history = [information_parsing.divide_information(e) for e in elements]
    args = util.resolve_full_arguments(history, defaults, aliases)
    for key in expected_dict:
        assert args[key] == expected_dict[key], f"Arg {key!r}: got {args[key]} expected {expected_dict[key]}"


def test_arg_basic_ops(backend):
    arg_tree_test(backend, "a3:aa0.2,ab+0.2,ac-0.2", {
        "aa": Decimal("0.2"),
        "ab": Decimal("0.2"),
        "ac": Decimal("-0.2"),
    })


def test_arg_reference(backend):
    arg_tree_test(backend, "1:ca0.2,cb2ca", {
        "ca": Decimal("0.2"),
        "cb": Decimal("0.4"),
    })


def test_arg_accumulation(backend):
    arg_tree_test(backend, "0:a+0.1 0:a+0.1 0:a+0.1", {
        "a": Decimal("0.3"),
    })


def test_arg_negation(backend):
    arg_tree_test(backend, "0:a-0.1", {
        "a": Decimal("-0.1"),
    })


def test_arg_mixed_ops(backend):
    arg_tree_test(backend, "0:a+0.1 0:a*0.5 0:a2.0", {
        "a": Decimal("1.1"),
    })


def test_arg_override(backend):
    arg_tree_test(backend, "0:a0.2 0:a*44 0:a1", {
        "a": Decimal("0.2"),
    })


def test_arg_defaults(backend):
    arg_tree_test(backend, "0", {
        "sus": Decimal("1.0"),
    }, defaults={"sus": Decimal("1.0")})


def test_arg_aliases(backend):
    arg_tree_test(backend, "0:>1.0", {
        "sus": Decimal("1.0"),
    }, aliases={">": "sus"})


def test_arg_aliased_defaults(backend):
    arg_tree_test(backend, "0:>1.0", {
        "sus": Decimal("1.0"),
    }, defaults={"sus": Decimal("2.0")}, aliases={">": "sus"})
