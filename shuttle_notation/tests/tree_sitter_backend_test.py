import pytest
from shuttle_notation.parsing.tree_sitter_backend import TreeSitterBackend
from shuttle_notation.parsing.element import Element, ElementType


@pytest.fixture(scope="session")
def backend():
    return TreeSitterBackend()


# ------------------------------------------------------------------
# Single notes
# ------------------------------------------------------------------

def test_bare_prefix(backend):
    el = backend.parse("a")
    assert el.type == ElementType.ATOMIC
    assert el.information == "a"


def test_prefix_index(backend):
    el = backend.parse("c4")
    assert el.type == ElementType.ATOMIC
    assert el.information == "c4"


def test_prefix_index_suffix(backend):
    el = backend.parse("c4sus")
    assert el.type == ElementType.ATOMIC
    assert el.information == "c4sus"


def test_bare_index(backend):
    el = backend.parse("42")
    assert el.type == ElementType.ATOMIC
    assert el.information == "42"


def test_float_index(backend):
    el = backend.parse("c4.5")
    assert el.type == ElementType.ATOMIC
    assert el.information == "c4.5"


def test_note_with_repeat(backend):
    el = backend.parse("c4*3")
    assert el.type == ElementType.ATOMIC
    assert el.information == "c4*3"


def test_note_with_args(backend):
    el = backend.parse("c4:dur0.5")
    assert el.type == ElementType.ATOMIC
    assert el.information == "c4:dur0.5"


def test_note_with_repeat_and_args(backend):
    el = backend.parse("c4*3:dur0.5,amp0.8")
    assert el.type == ElementType.ATOMIC
    assert el.information == "c4*3:dur0.5,amp0.8"


def test_underscore_prefix(backend):
    el = backend.parse("a_1")
    assert el.type == ElementType.ATOMIC
    assert el.information == "a_1"


def test_underscore_only_prefix(backend):
    el = backend.parse("_a4")
    assert el.type == ElementType.ATOMIC
    assert el.information == "_a4"


# ------------------------------------------------------------------
# Sections
# ------------------------------------------------------------------

def test_empty_section(backend):
    el = backend.parse("()")
    assert el.type == ElementType.SECTION
    assert el.information == ""
    assert len(el.elements) == 0


def test_single_note_section(backend):
    el = backend.parse("(c4)")
    assert el.type == ElementType.SECTION
    assert el.information == ""
    assert len(el.elements) == 1
    assert el.elements[0].information == "c4"


def test_multi_note_section(backend):
    el = backend.parse("(c4 d4 e4)")
    assert el.type == ElementType.SECTION
    assert len(el.elements) == 3
    assert [e.information for e in el.elements] == ["c4", "d4", "e4"]


def test_section_with_suffix(backend):
    el = backend.parse("(c4 d4)sus")
    assert el.type == ElementType.SECTION
    assert el.information == "sus"
    assert len(el.elements) == 2


def test_section_with_repeat(backend):
    el = backend.parse("(c4 d4)*2")
    assert el.type == ElementType.SECTION
    assert el.information == "*2"
    assert len(el.elements) == 2


def test_section_with_args(backend):
    el = backend.parse("(c4 d4):dur0.5")
    assert el.type == ElementType.SECTION
    assert el.information == ":dur0.5"
    assert len(el.elements) == 2


def test_section_suffix_repeat_args(backend):
    el = backend.parse("(c4 d4)sus*2:dur0.5")
    assert el.type == ElementType.SECTION
    assert el.information == "sus*2:dur0.5"
    assert len(el.elements) == 2


# ------------------------------------------------------------------
# Alternations
# ------------------------------------------------------------------

def test_basic_alternation(backend):
    el = backend.parse("(c4 / d4)")
    assert el.type == ElementType.SECTION
    assert len(el.elements) == 1
    alt = el.elements[0]
    assert alt.type == ElementType.ALTERNATION_SECTION
    assert len(alt.elements) == 2


def test_three_way_alternation(backend):
    el = backend.parse("(c4 / d4 / e4)")
    assert el.type == ElementType.SECTION
    alt = el.elements[0]
    assert alt.type == ElementType.ALTERNATION_SECTION
    assert len(alt.elements) == 3


def test_alternation_with_sections(backend):
    el = backend.parse("((c4 d4) / (e4 f4))")
    assert el.type == ElementType.SECTION
    alt = el.elements[0]
    assert alt.type == ElementType.ALTERNATION_SECTION
    assert len(alt.elements) == 2
    for arm in alt.elements:
        assert arm.type == ElementType.SECTION
        assert len(arm.elements) == 2


def test_alternation_section_with_args(backend):
    el = backend.parse("(d4 / g4):0.5")
    assert el.type == ElementType.SECTION
    assert el.information == ":0.5"
    alt = el.elements[0]
    assert alt.type == ElementType.ALTERNATION_SECTION
    assert len(alt.elements) == 2


# ------------------------------------------------------------------
# Multi-element at root
# ------------------------------------------------------------------

def test_two_elements_at_root(backend):
    el = backend.parse("c4 d4")
    assert el.type == ElementType.SECTION
    assert len(el.elements) == 2
    assert el.elements[0].information == "c4"
    assert el.elements[1].information == "d4"


def test_note_and_section_at_root(backend):
    el = backend.parse("c4 (d4 e4)")
    assert el.type == ElementType.SECTION
    assert len(el.elements) == 2
    assert el.elements[0].information == "c4"
    assert el.elements[1].type == ElementType.SECTION
    assert len(el.elements[1].elements) == 2


# ------------------------------------------------------------------
# Empty / degenerate
# ------------------------------------------------------------------

def test_empty_string(backend):
    el = backend.parse("")
    assert el.type == ElementType.SECTION
    assert len(el.elements) == 0


def test_whitespace_only(backend):
    el = backend.parse("   ")
    assert el.type == ElementType.SECTION
    assert len(el.elements) == 0


# ------------------------------------------------------------------
# Trailing-info absorption (Phase-2 fallback)
# ------------------------------------------------------------------

def test_note_trailing_raw_info(backend):
    """Note with unparseable info absorbs ERROR text."""
    el = backend.parse("a4:bad*stuff")
    assert el.type == ElementType.ATOMIC
    assert el.information == "a4:bad*stuff"


def test_section_trailing_raw_info(backend):
    """Section with unparseable info absorbs ERROR text."""
    el = backend.parse("(a b):ss*s")
    assert el.type == ElementType.SECTION
    assert el.information == ":ss*s"
    assert len(el.elements) == 2


# ------------------------------------------------------------------
# Malformed input → "Malformed input" exception
# ------------------------------------------------------------------

def test_missing_close_paren(backend):
    with pytest.raises(Exception, match="Malformed input"):
        backend.parse("(a c v")


def test_bare_slash_inside_nested(backend):
    with pytest.raises(Exception, match="Malformed input"):
        backend.parse("(((((/)))))")


def test_double_slash(backend):
    with pytest.raises(Exception, match="Malformed input"):
        backend.parse("a / / b")


def test_garbage_between_elements(backend):
    with pytest.raises(Exception, match="Malformed input"):
        backend.parse("a3 ,, b")


# ------------------------------------------------------------------
# Decompilation round-trips
# ------------------------------------------------------------------

def test_decompile_note(backend):
    el = backend.parse("c4")
    assert el.decompile() == "c4"


def test_decompile_section(backend):
    el = backend.parse("(c4 d4)")
    assert el.decompile() == "(c4 d4)"


def test_decompile_alternation(backend):
    el = backend.parse("(c4 / d4)")
    # The section wrapper around the alternation adds outer parens
    assert el.decompile() == "((c4 / d4))"


def test_decompile_nested(backend):
    el = backend.parse("(c4 (d4 e4))")
    assert el.decompile() == "(c4 (d4 e4))"


def test_decompile_note_with_args(backend):
    el = backend.parse("c4:dur0.5")
    assert el.decompile() == "c4:dur0.5"


# ------------------------------------------------------------------
# Information array / parent linkage
# ------------------------------------------------------------------

def test_parent_linkage_section(backend):
    el = backend.parse("(c4 d4):dur0.5")
    assert el.elements[0].parent is el
    assert el.elements[1].parent is el


def test_parent_linkage_nested(backend):
    el = backend.parse("((c4):dur0.3):dur0.5")
    inner = el.elements[0]
    assert inner.parent is el
    assert inner.information == ":dur0.3"
    note = inner.elements[0]
    assert note.parent is inner


def test_information_array_ordered(backend):
    el = backend.parse("((c4):b):a")
    inner = el.elements[0]
    note = inner.elements[0]
    info = note.get_information_array_ordered()
    # note stores full raw text "c4", inner has ":b", outer has ":a"
    assert info == ["c4", ":b", ":a"], info


# ------------------------------------------------------------------
# Deeply nested sections
# ------------------------------------------------------------------

def test_deeply_nested(backend):
    el = backend.parse("((c4 d4) (e4 f4))")
    assert el.type == ElementType.SECTION
    assert len(el.elements) == 2
    for child in el.elements:
        assert child.type == ElementType.SECTION
        assert len(child.elements) == 2


def test_nested_alternation_in_section(backend):
    el = backend.parse("(a (b / c))")
    assert len(el.elements) == 2
    assert el.elements[0].information == "a"
    # (b / c) is a section wrapping an alternation
    inner = el.elements[1]
    assert inner.type == ElementType.SECTION
    assert len(inner.elements) == 1
    assert inner.elements[0].type == ElementType.ALTERNATION_SECTION
    assert len(inner.elements[0].elements) == 2
