# Plan: Adopt tree-sitter as the Python parser backend

## Goal

Replace the hand-written `section_parsing.build_tree()` and
`information_parsing.divide_information()` with a parser backed by
tree-sitter, making `grammar.js` in `tree-sitter-shuttle-notation/` the
single source of truth for the language. All semantic stages (alternation
expansion, argument resolution) remain unchanged — only the front-end
parser is swapped.

## Architecture

```
              source_string
                    │
                    ▼
     ┌──────────────────────────┐
     │  tree-sitter (wasm)      │  ← new: grammar.js compiled to wasm
     │  parses into CST         │
     └──────────┬───────────────┘
                │
                ▼
     ┌──────────────────────────┐
     │  cst_to_element_tree()   │  ← new: CST → Element tree walker
     │  builds Element objects  │
     └──────────┬───────────────┘
                │
                ▼
     ┌──────────────────────────┐
     │  TreeExpander            │  ← unchanged (util.py)
     │  alternation expansion   │
     └──────────┬───────────────┘
                │
                ▼
     ┌──────────────────────────┐
     │  resolve_full_arguments  │  ← unchanged (util.py)
     │  arg inheritance / refs  │
     └──────────┬───────────────┘
                │
                ▼
            ResolvedElement[]
```

**Why an intermediate Element tree?** The existing `TreeExpander` and
`resolve_full_arguments` are well-tested and correct. They operate on the
`Element` tree (with parent references for inheritance walks). Rather than
rewriting both semantic stages to walk the CST directly, we build the
`Element` tree from the CST — a mechanical, testable transformation.

---

## Phase 1 — Update the tree-sitter grammar ✅ *Complete*

The grammar at `tree-sitter-shuttle-notation/grammar.js` has been updated.
All 31 corpus tests pass. The Python parser's 6 tests still pass unchanged.

### Changes made

#### 1a. `prefix`, `suffix`, `arg_name`, `ref` regexes

| Token | Old regex | New regex | Rationale |
|---|---|---|---|
| `prefix` | `[a-zA-Z_.]+` | `[a-zA-Z_]+` | Spec identifiers use `_`, not `.`. Digits excluded to avoid ambiguity with index. |
| `suffix` | `[a-zA-Z_]+` | `[a-zA-Z_][a-zA-Z0-9_]*` | Full identifier — no adjacent token to compete with. |
| `arg_name` | `[a-zA-Z]+` | `[a-zA-Z_]+` | Added `_`. Digits excluded: in `amp0.5`, alpha-only match gives arg_name=`amp`, number=`0.5`. With digits allowed, `amp0` would greedily match, leaving `.5` unparseable. |
| `ref` | `[a-zA-Z]+` | `[a-zA-Z_][a-zA-Z0-9_]*` | Full identifier — ref follows a number, so no digit-ambiguity. |

#### 1b. Prefix/suffix disambiguation (deferred to CST walker)

The Python heuristic ("everything before the first digit is prefix,
everything after is suffix") cannot be expressed cleanly in the grammar
without making `_note_core` an opaque token (which degrades highlighting).

**Decision:** The grammar keeps its structural assignment (bare `a` →
prefix, bare `x` in `x:16` → prefix). The CST walker in Phase 2
reassigns prefix/suffix to match Python's heuristic when the two differ.
This is a small, localized fix in the walker.

#### 1c. Section raw info

Edge cases like `():fff` and `(a b):ss*s` don't parse as structured args.
Tree-sitter's LR parser with error recovery handles these by producing
ERROR or MISSING nodes. The CST walker detects these and falls back to
raw text extraction.

Attempting a `raw_info` fallback rule with `choice($.info, $.raw_info)`
failed because both start with `":"` and LR(1) can't disambiguate without
more lookahead.

#### 1d. Added test corpus entries

31 total test cases (up from 22):

- Notes: prefix with underscore (`a_1`), underscore-only prefix (`_a4`),
  bare string treated as prefix (`x:16`), bare prefix only (`a`), empty source
- Arguments: arg name with underscore (`amp_0.5`), ref with underscore
  (`time_2`), arg name with digits (documented as untestable limitation)
- Sections: raw non-arg info (`():fff`), raw info fallback to top-level
  error (`(a b):ss*s`)

### Known grammar limitations

These are documented and handled by the CST walker:

1. **Bare non-numeric → prefix, not suffix:** `"a"` parses as prefix.
   Python treats it as suffix. CST walker reassigns.
2. **Digits in arg names:** `test1` can't be parsed as an arg name
   because digits are ambiguous with the number value. Use `test_1`.
3. **Section raw info:** Non-arg text after `:` on a section produces
   ERROR/MISSING nodes. CST walker extracts raw text from these.

### Grammar distribution

The zed extension's copy of the grammar (`zed-extension-shuttle-syntax/`)
has been updated with the new `grammar.js`, generated parser files, and
regenerated `shuttle.wasm`.

---

## Phase 2 — Build the CST-to-Element walker

New file: `shuttle_notation/parsing/tree_sitter_backend.py`

Responsibilities:
- Load the shuttle wasm grammar via the `tree-sitter` pip package
- Accept a `source_string` → parse via `tree_sitter.Parser`
- Walk the CST recursively, producing `Element` objects (same types,
  same parent-linkage as today)
- Detect `ERROR` nodes and raise `Exception("Malformed input")` with
  position info
- Handle the prefix/suffix reassignment for the bare-non-numeric edge case

### CST node → Element type mapping

| CST node | Element type | Notes |
|---|---|---|
| `note` | `ATOMIC` | Extract prefix/index/suffix/repeat/info from child nodes |
| `section` | `SECTION` | Recurse into body; extract suffix/repeat/info from trailing nodes |
| `alternation` | `ALTERNATION_SECTION` | Each child sequence → one alternation arm |
| `arg` | stored on parent | Not an Element itself; used to reconstruct `information` string |

### Prefix/suffix reassignment

For each `note` node, apply Python's heuristic to the raw text:
- Characters before the first digit → `prefix`
- First digit sequence → `index`
- Everything after the first digit → `suffix`

This falls back to: if no digit found, everything is `suffix` (even if
tree-sitter parsed it as `prefix`).

### Information string reconstruction

Reconstruct `Element.information` as a canonical string from the CST
children, keeping `divide_information` operational for downstream code
that calls `get_information_array_ordered`:

```
canonical = prefix + index + suffix
if repeat:   canonical += "*" + repeat_count
if info:     canonical += ":" + args_string
```

---

## Phase 3 — Wire into Parser

Modify `full_parse.py`:

```python
class Parser:
    def __init__(self):
        self.arg_aliases = {}
        self.arg_defaults = {}
        self._ts_backend = TreeSitterBackend()  # loads wasm once

    def parse(self, source_string: str) -> list[ResolvedElement]:
        top_element = self._ts_backend.parse(source_string)
        tree = util.TreeExpander()
        sequence = tree.tree_expand(top_element)
        return [self.resolve(e) for e in sequence]

    # resolve() stays identical
```

The old `section_parsing.py`, `information_parsing.py`, and `cursor.py`
can then be deprecated and removed.

---

## Phase 4 — Tests

- Existing 6 Python tests must pass without modification
- Add `tests/tree_sitter_backend_test.py` for the CST → Element mapping
  (edge cases: empty input, bare prefix, section raw info, alternations,
  nested sections)
- Verify the prefix/suffix reassignment is correct for all edge cases
- Test that ERROR nodes produce the same `"Malformed input"` exceptions

---

## Phase 5 — Cleanup

- Remove `section_parsing.py`, `information_parsing.py`, `cursor.py`
- Remove `util.section_split()` (no longer needed)
- Optionally inline `divide_information` logic into the CST walker
- Update `pyproject.toml`: add `tree-sitter` dependency
- Bundle the wasm file in the Python package or download on first use
- Update `README.md` with new architecture

---

## Open questions

1. **Wasmer vs wasmtime?** The `tree-sitter` pip package supports
   multiple wasm runtimes. The default (wasmtime) should work on most
   platforms. Benchmark if performance is a concern.
2. **Wasm distribution:** Bundle in package vs download on install?
   Bundling is simpler for users but increases package size (~7 KB for
   the shuttle wasm, which is negligible).
3. **Performance:** Wasm parsing has ~100µs overhead per parse. For batch
   processing, a native C extension may be faster. Worth benchmarking.

## Migration timeline

```
Phase 1 (grammar updates)       ✅ complete (31 corpus tests, 6 Python tests)
Phase 2 (CST walker)            → 1-2 days
Phase 3 (wire into Parser)      → half day
Phase 4 (tests)                 → half day
Phase 5 (cleanup)               → half day
```
