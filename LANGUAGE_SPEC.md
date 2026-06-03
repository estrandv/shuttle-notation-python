# Shuttle Notation Language Specification

**Version:** 1.0  
**Last Updated:** 2026-06-03

## Table of Contents

1. [Overview](#overview)
2. [Lexical Structure](#lexical-structure)
3. [Grammar](#grammar)
4. [Semantic Rules](#semantic-rules)
5. [Data Model](#data-model)
6. [Examples](#examples)
7. [Implementation Notes](#implementation-notes)

---

## Overview

Shuttle Notation is a domain-specific language for defining sequential data with rich metadata. It is designed to be:

- **Concise**: Easy to type and read
- **Expressive**: Supports complex patterns through alternations and repetitions
- **Flexible**: Purpose-agnostic sequential data with user-defined arguments
- **Hierarchical**: Nested sections with inherited properties

### Primary Use Case

Musical note sequencing, but applicable to any sequential, time-based data.

### Core Features

1. **Atomic Elements**: Individual sequence entries with indices
2. **Arguments**: Named numerical parameters (e.g., `amplitude`, `duration`)
3. **Sections**: Grouping with shared properties
4. **Alternations**: Patterns that vary on each iteration
5. **Repetition**: Compact notation for repeated patterns
6. **Inheritance**: Arguments cascade through nested structures

---

## Lexical Structure

### Tokens

#### Whitespace
- **Space** (` `): Primary element separator
- **Newlines/Tabs**: Treated as whitespace, no semantic meaning

#### Identifiers
- **Pattern**: `[a-zA-Z_][a-zA-Z0-9_]*`
- **Examples**: `c4`, `note`, `amplitude`, `sus`
- **Usage**: Element prefixes, argument names

#### Numbers
- **Pattern**: `[0-9]+(\.[0-9]+)?`
- **Examples**: `1`, `3.14`, `0.5`
- **Usage**: Indices, argument values, repetition counts

#### Operators and Delimiters
- `(` `)`: Section grouping
- `/`: Alternation separator
- `*`: Repetition operator
- `:`: Argument/information separator
- `+` `-` `*` `=`: Argument operators for relative modifications
- `,`: Argument separator
- `.`: Decimal point in numbers

#### Comments
- Not currently defined in the language

---

## Grammar

### EBNF Notation

```ebnf
(* Top-level *)
sequence          = element_list ;

element_list      = element { whitespace element } ;

element           = atomic_element
                  | section ;

(* Atomic Elements *)
atomic_element    = [ prefix ] [ index ] [ suffix ] [ repeat ] [ information ] ;

prefix            = identifier ;

index             = number ;

suffix            = identifier ;

information       = ":" args ;

(* Arguments *)
args              = arg { "," arg } ;

argument          = [ arg_name ] [ operator ] number [ ref ] ;

arg_name          = identifier ;

operator          = "+" | "-" | "*" | "=" ;

ref               = identifier ;

(* Sections *)
section           = "(" section_content ")" [ suffix ] [ repeat ] [ information ] ;

section_content   = alternation_list
                  | element_list ;

alternation_list  = element_list { "/" element_list } ;

repeat            = "*" number ;

(* Primitives *)
identifier        = letter { letter | digit | "_" } ;

number            = digit { digit } [ "." digit { digit } ] ;

letter            = "a" | "b" | ... | "z" | "A" | "B" | ... | "Z" | "_" ;

digit             = "0" | "1" | ... | "9" ;

whitespace        = " " | "\t" | "\n" | "\r" ;
```

### Precedence and Associativity

1. **Parentheses** `( )`: Highest precedence, creates scope
2. **Repetition** `*`: Applies to immediately preceding element/section
3. **Information** `:`: Binds to immediately preceding element/section
4. **Alternation** `/`: Separates alternatives within a section
5. **Whitespace**: Lowest precedence, separates elements

---

## Semantic Rules

### Element Resolution

Each element in the sequence resolves to a **ResolvedElement** with:
- `prefix`: String identifier (default: `""`)
- `index`: Integer or float (default: `0`)
- `suffix`: String identifier (default: `""`)
- `args`: Dictionary of argument name → value

### Argument Inheritance

Arguments flow **top-down** through the tree structure:

1. **Default arguments**: Provided at parse time
2. **Section arguments**: Override defaults for all children
3. **Element arguments**: Override section/default arguments

#### Argument Operators

Arguments can use operators to modify inherited values:

- `+`: Add to inherited value
- `-`: Subtract from inherited value (or negate if no inherited value)
- `*`: Multiply inherited value
- `=`: Explicitly set (same as no operator)

```
"c:amp0.5 (d:amp+0.2 e:amp-0.1 f:amp*2)"
```

- `c` has `amp=0.5`
- `d` has `amp=0.7` (0.5 + 0.2)
- `e` has `amp=0.4` (0.5 - 0.1)
- `f` has `amp=1.0` (0.5 * 2)

#### Argument References

Arguments can reference other resolved argument values:

```
"c:time1.0,sus0.5time"
```

- `sus` is set to `0.5 * time` = `0.5 * 1.0` = `0.5`

The syntax is: `argname<value><referenced_arg_name>`

References are resolved after all non-referential arguments are computed.

### Alternations

Sections with `/` create **alternating patterns**:

```
"(a / b / c)*6"
```

Expands to: `a b c a b c`

- Each iteration cycles through alternatives
- Nested alternations multiply combinations

### Repetition

The `*` operator repeats the preceding element or section:

```
"a*3"        → a a a
"(a b)*2"    → a b a b
```

Note: The repetition syntax is `*N` not `xN` as shown in some examples.

### Section Expansion

Sections are expanded into flat sequences:

1. **Parse** section content into tree
2. **Expand** alternations based on repetition count
3. **Flatten** into sequence of atomic elements
4. **Resolve** arguments for each element

---

## Data Model

### Element Types (Enum)

```python
class ElementType(Enum):
    ATOMIC       # Single element
    SECTION      # Grouped elements
    ALTERNATION  # Multiple alternatives
```

### Element Structure

```python
class Element:
    elements: list[Element]      # Child elements (for sections)
    information: str             # Raw information string
    type: ElementType            # Element classification
```

### Resolved Element

```python
@dataclass
class ResolvedElement:
    prefix: str                  # Element identifier
    index: int | float           # Primary value
    suffix: str                  # Additional identifier
    args: dict[str, Decimal]     # Named arguments
```

### Element Information

```python
@dataclass
class ElementInformation:
    prefix: str = ""              # Contents before first numeric
    index_string: str = ""        # First numeric or special symbol
    suffix: str = ""              # Contents after first numeric
    repetition: int = 1           # Contents after "*", before ":"
    arg_source: str = ""          # Final contents after ":"
```

### Dynamic Arguments

```python
@dataclass
class DynamicArg:
    value: Decimal
    operator: str = ""            # "+", "-", "*", "=" or ""
    other_arg_reference: str = "" # Reference to another arg name
```

---

## Examples

### Basic Sequences

```
"c d e f"
→ [c, d, e, f]

"1 2 3 4"
→ [1, 2, 3, 4]

"c4 d4 e4 f4"
→ [c4, d4, e4, f4]
```

### With Arguments

```
"c:amp0.5 d:amp0.8"
→ c with amp=0.5, d with amp=0.8

"c:amp0.5,dur2 d"
→ c with amp=0.5, dur=2; d inherits nothing

"c:0.5"
→ c with first unnamed arg (typically "time") = 0.5
```

Note: Multiple arguments are separated by commas. The first unnamed argument defaults to "time" if no name is provided.

### Sections with Inheritance

```
"(c d e):amp0.5"
→ All three notes have amp=0.5

"(c:amp0.8 d e):amp0.5"
→ c has amp=0.8, d and e have amp=0.5
```

### Relative Arguments

```
"c:amp0.5 (d:amp+0.2 e:amp-0.1)"
→ c: amp=0.5, d: amp=0.7, e: amp=0.4
```

### Argument References

```
"c:time1.0,sus0.5time"
→ c: time=1.0, sus=0.5 (0.5 * time)
```

### Alternations

```
"(a / b)*4"
→ a b a b

"(a b / c d)*2"
→ a b c d

"(a / b / c)*5"
→ a b c a b
```

### Repetition

```
"a*3"
→ a a a

"(a b)*2"
→ a b a b

"(a / b)*2:amp0.5"
→ a b, both with amp=0.5
```

### Complex Example

```
"c3:sus3.4 c3:0.5 (a3 / b3:sus+1 / f3 / g3)*2:0.5,sus0.2"
```

Breakdown:
- `c3:sus3.4` → c, index=3, sus=3.4
- `c3:0.5` → c, index=3, arg value 0.5 (unnamed, defaults to "time")
- Section with 4 alternations, repeated 2 times
- Section has args: unnamed=0.5, sus=0.2
- `b3:sus+1` → b, index=3, sus=0.2+1=1.2 (relative)

---

## Implementation Notes

### Parser Architecture

The reference implementation uses a multi-stage parser:

1. **Lexical Analysis** (`cursor.py`): Character-by-character scanning with `Cursor` class
2. **Section Parsing** (`section_parsing.py`): Build tree structure from `()` and `/` syntax
3. **Information Parsing** (`information_parsing.py`): Extract prefix, index, suffix, repetition, and arguments
4. **Tree Expansion** (`util.py`): Handle alternations and repetitions with `TreeExpander` class
5. **Resolution** (`full_parse.py`): Produce final `ResolvedElement` list with inherited arguments

### Parsing Stages Detail

**Stage 1: Section Parsing**
- Uses `section_split()` to divide input by spaces (respecting parentheses)
- Builds tree of `Element` objects with types: ATOMIC, SECTION, ALTERNATION_SECTION
- Handles nested sections recursively

**Stage 2: Information Division**
- Uses `divide_information()` to parse each element's information string
- Extracts: prefix, index_string, suffix, repetition, arg_source
- Sections have no prefix/index, only suffix and args

**Stage 3: Tree Expansion**
- `TreeExpander.tree_expand()` flattens the tree into a sequence
- Handles alternations by cycling through alternatives
- Applies repetitions at each level
- Uses "ticking" mechanism to track alternation state

**Stage 4: Argument Resolution**
- `resolve_full_arguments()` walks up the tree collecting argument definitions
- Applies operators (+, -, *, =) to modify inherited values
- Resolves argument references in two passes
- Returns dict of argument name → Decimal value

**Stage 5: Element Resolution**
- Converts each `Element` to `ResolvedElement`
- Combines information and resolved arguments
- Produces final flat list ready for interpretation

### Key Classes

- `Cursor`: Stateful string scanner
- `Element`: Tree node representation
- `Parser`: Main entry point with `parse()` method
- `TreeExpander`: Handles alternation expansion
- `ResolvedElement`: Final output format

### Argument Aliases

The parser supports argument name aliases:

```python
parser = Parser()
parser.arg_aliases = {"amp": "amplitude", "dur": "duration"}
```

This allows `amp` to be used in notation but resolved as `amplitude`.

### Default Arguments

Default values can be provided at parse time:

```python
parser.parse("c d e", default_args={"amp": 0.5, "dur": 1.0})
```

### Edge Cases

1. **Empty sections**: `()` is valid, produces no elements
2. **Whitespace**: Multiple spaces treated as single separator
3. **Malformed input**: Parser attempts to handle gracefully
4. **Nested alternations**: Multiply to create all combinations
5. **Zero repetition**: `*0` produces no elements

### Tree-Sitter Considerations

For implementing a tree-sitter grammar:

1. **Whitespace handling**: Space is significant as separator
2. **Precedence**: Parentheses > repetition > information > alternation
3. **Ambiguity**: Identifiers vs numbers resolved by first character
4. **Nesting**: Sections can nest arbitrarily deep
5. **Context-free**: Grammar is context-free, semantics require tree walking

### Extension Points

The language is designed to be extensible:

1. **New argument types**: Currently only numeric
2. **Additional operators**: Could add more relative operators
3. **Comments**: Could add `#` or `//` style comments
4. **Macros**: Could add named pattern definitions
5. **Imports**: Could reference external notation files

---

## Formal Grammar Summary

For quick reference, the core grammar in compact form:

```
sequence    ::= element*
element     ::= atomic | section
atomic      ::= prefix? index? suffix? repeat? info?
section     ::= '(' content ')' suffix? repeat? info?
content     ::= alternation | sequence
alternation ::= sequence ('/' sequence)+
repeat      ::= '*' number
info        ::= ':' args
args        ::= arg (',' arg)*
arg         ::= [name] [operator] number [ref]
operator    ::= '+' | '-' | '*' | '='
ref         ::= identifier
prefix      ::= identifier
suffix      ::= identifier
name        ::= identifier
index       ::= number
```

---

## Version History

- **1.0** (2026-06-03): Initial specification based on reference implementation

---

## References

- Reference Implementation: `shuttle_notation/parsing/`
- Test Suite: `shuttle_notation/tests/`
- Examples: `shuttle_notation/parsing/examples.py`
