# AGENTS.md — Shuttle Notation Python

## Directory Structure

```
shuttle_notation/
  __init__.py              # Exports: Parser, ResolvedElement
  parsing/
    __init__.py
    element.py             # Element, ResolvedElement, ElementType
    tree_sitter_backend.py # TreeSitterBackend (CST -> Element tree)
    full_parse.py          # Parser class (high-level API)
    information_parsing.py # Information, parse_information()
    examples.py            # Example parse trees for testing
    util.py                # tree_expansion, information_history, arg resolution
  tests/
    tree_sitter_backend_test.py
    full_parse_test.py
    information_parsing_test.py
    util_test.py
```

## Key Entry Points

- `shuttle_notation.Parser` — main public API
- `shuttle_notation.parsing.tree_sitter_backend.TreeSitterBackend` — low-level CST parsing via tree-sitter
- `shuttle_notation.parsing.element.Element` — tree node (type, information, children)

## Data Flow

```
Source text
  -> TreeSitterBackend.parse() -> Element tree  (CST level, raw info strings)
  -> Parser.parse()            -> ResolvedElement tree  (info parsed to structured data)
```

## Key Types

- `ElementType.ATOMIC` — leaf node with index/information
- `ElementType.SECTION` — container with children
- `ElementType.ALTERNATION_SECTION` — alternation grouping
- `Information` — parsed `:info` suffix: indices, named_args, repeat, override

## Dependencies

- `tree-sitter-shuttle-notation` >=0.3.0 (PyPI)
- `tree-sitter` >=0.25,<0.26

## Running Tests

```bash
~/mypython/bin/python -m pytest shuttle_notation/tests/ -v
```

## Common Patterns

- To add a new parsing feature: modify `grammar.js` in `tree-sitter-shuttle-notation`, then update `tree_sitter_backend.py` to handle the new CST node type
- Information strings (`:idx:arg1=val arg2=val`) are parsed in `information_parsing.py`
- Alternation nesting is handled via `ElementType.ALTERNATION_SECTION` with `/`-separated arms
