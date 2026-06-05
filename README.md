# Shuttle Notation

A Python library for parsing and manipulating Shuttle Notation — a shorthand DSL for defining sequential data with rich metadata: indices, named arguments, alternations, repetition, and section inheritance.

Designed primarily for musical note sequencing (think typed sheet music), but purpose-agnostic.

## Example

```
c3:sus3.4 c3:0.5 (a3 / b3:+sus1 / f3 / g3)x2:0.5sus0.2
```

## Architecture

- **`shuttle_notation.parsing.tree_sitter_backend`** — CST-based parser using the tree-sitter grammar (`tree-sitter-shuttle-notation` published as a pip package). Produces an `Element` tree from source text.
- **`shuttle_notation.parsing.element`** — Core data model: `Element` (with type `ATOMIC`, `SECTION`, `ALTERNATION_SECTION`), `ResolvedElement` (with resolved children), and `ElementType`.
- **`shuttle_notation.parsing.full_parse`** — High-level `Parser` that wraps the tree-sitter backend and resolves information strings into structured `Information` objects (indices, args, aliases).
- **`shuttle_notation.parsing.information_parsing`** — Parses the `:info` suffix string into structured data (indices, named args, repeats, overrides).
- **`shuttle_notation.parsing.util`** — Utilities for expanding alternation trees into flat histories and applying arg defaults/aliases.

## Dependencies

- [tree-sitter-shuttle-notation](https://pypi.org/project/tree-sitter-shuttle-notation/) (PyPI) — the canonical tree-sitter grammar
- [tree-sitter](https://tree-sitter.github.io/) Python bindings (>=0.25,<0.26)

## Usage

```python
from shuttle_notation import Parser

parser = Parser()
result = parser.parse("c4 d4 e4 f4")
# result is a ResolvedElement tree
```

## Tests

```bash
cd shuttle-notation-python
~/mypython/bin/python -m pytest
```

## Spec / Grammar

The canonical language specification lives in the grammar repo:
- [tree-sitter-shuttle-notation](https://github.com/estrandv/tree-sitter-shuttle-notation)
