import ctypes
import os
import subprocess
import tempfile
from pathlib import Path

from tree_sitter import Language, Parser, Node

from shuttle_notation.parsing.element import Element, ElementType

_PACKAGE_DIR = Path(__file__).resolve().parent.parent
_VENDOR_DIR = _PACKAGE_DIR / "vendor"
_SIBLING_DIR = _PACKAGE_DIR.parent.parent / "tree-sitter-shuttle-notation" / "src"
_SO_PATH = _PACKAGE_DIR / "shuttle.so"


def _find_parser_source():
    vendored = _VENDOR_DIR / "parser.c"
    if vendored.exists():
        return vendored, str(_VENDOR_DIR)
    sibling = _SIBLING_DIR / "parser.c"
    if sibling.exists():
        return sibling, str(_SIBLING_DIR)
    raise RuntimeError(
        "Could not find tree-sitter-shuttle-notation parser source. "
        "Expected either vendored at shuttle_notation/vendor/parser.c "
        "or sibling tree-sitter-shuttle-notation/src/parser.c"
    )


def _build_shared_lib():
    if _SO_PATH.exists():
        return str(_SO_PATH)
    parser_c, include_dir = _find_parser_source()
    result = subprocess.run(
        [
            "cc", "-shared", "-fPIC", "-o", str(_SO_PATH),
            str(parser_c),
            f"-I{include_dir}",
        ],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to build shuttle parser: {result.stderr}")
    return str(_SO_PATH)


def _load_language():
    lib_path = _build_shared_lib()
    lib = ctypes.CDLL(lib_path)
    func = lib.tree_sitter_shuttle
    func.restype = ctypes.c_void_p
    ptr = func()
    return Language(ptr)


class TreeSitterBackend:
    def __init__(self):
        self._lang = _load_language()
        self._parser = Parser()
        self._parser.language = self._lang

    def parse(self, source_string: str) -> Element:
        tree = self._parser.parse(source_string.encode("utf-8"))
        root = tree.root_node
        return self._build_element_tree(root)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _pos_str(node: Node) -> str:
        return f"({node.start_point.row},{node.start_point.column})"

    # ------------------------------------------------------------------
    # Top-level dispatch
    # ------------------------------------------------------------------

    def _build_element_tree(self, cst_node: Node) -> Element:
        element = Element()
        element.parent = None

        match cst_node.type:
            case "root":
                return self._process_root(cst_node)

            case "note":
                element.type = ElementType.ATOMIC
                element.information = cst_node.text.decode()

            case "section":
                element.type = ElementType.SECTION
                body_children = []
                trailing_parts = []
                after_paren = False
                missing_paren = False
                for c in cst_node.children:
                    if c.type == ")":
                        if c.text.decode() == "":
                            missing_paren = True
                        after_paren = True
                    elif c.type in ("(", ")"):
                        pass
                    elif after_paren:
                        trailing_parts.append(c)
                    else:
                        body_children.append(c)

                if missing_paren:
                    raise Exception(
                        f"Malformed input — section without closing ')' "
                        f"at {self._pos_str(cst_node)}"
                    )

                for c in body_children:
                    if c.type == "ERROR":
                        raise Exception(
                            f"Malformed input at {self._pos_str(c)}"
                        )

                self._process_section_body(element, body_children)

                if trailing_parts:
                    element.information = "".join(
                        c.text.decode() for c in trailing_parts
                    )
                else:
                    element.information = ""

            case "alternation":
                element.type = ElementType.ALTERNATION_SECTION
                self._process_alternation(element, cst_node)

            case _:
                pass

        return element

    # ------------------------------------------------------------------
    # Root-level processing  (absorbs trailing-ERROR raw-info)
    # ------------------------------------------------------------------

    def _process_root(self, root_node: Node) -> Element:
        element = Element()
        element.type = ElementType.SECTION

        children = list(root_node.children)
        if not children:
            return element

        processed = []  # list[Element]
        i = 0
        while i < len(children):
            c = children[i]

            if c.type in ("note", "section"):
                sub = self._build_element_tree(c)

                # Peek at next child: trailing ERROR *starting with ":"
                # is raw-section-info that tree-sitter couldn't parse.
                if i + 1 < len(children):
                    nxt = children[i + 1]
                    if nxt.type == "ERROR" and nxt.text.decode().startswith(":"):
                        raw = nxt.text.decode()
                        if sub.type == ElementType.ATOMIC:
                            sub.information = c.text.decode() + raw
                        else:
                            sub.information = raw
                        i += 1  # consume the ERROR

                processed.append(sub)

            elif c.type == "ERROR":
                raise Exception(
                    f"Malformed input at {self._pos_str(c)}"
                )

            # Skip any other node types (implicit whitespace, etc.)
            i += 1

        if not processed:
            return element
        if len(processed) == 1:
            return processed[0]

        for sub in processed:
            sub.parent = element
            element.elements.append(sub)
        return element

    # ------------------------------------------------------------------
    # Section / alternation helpers
    # ------------------------------------------------------------------

    def _process_section_body(self, parent: Element, body_nodes: list):
        for node in body_nodes:
            if node.type in ("note", "section"):
                sub = self._build_element_tree(node)
                sub.parent = parent
                parent.elements.append(sub)
            elif node.type == "alternation":
                alt = self._build_element_tree(node)
                alt.parent = parent
                parent.elements.append(alt)
            elif node.type == "ERROR":
                raise Exception(
                    f"Malformed input at {self._pos_str(node)}"
                )

    def _process_alternation(self, alt_element: Element, cst_node: Node):
        current_arm = []
        for c in cst_node.children:
            if c.type == "/":
                self._flush_arm(alt_element, current_arm)
                current_arm = []
            elif c.type in ("note", "section"):
                current_arm.append(c)
            elif c.type == "ERROR":
                raise Exception(
                    f"Malformed input at {self._pos_str(c)}"
                )

        self._flush_arm(alt_element, current_arm)

    def _flush_arm(self, alt_element: Element, arm_nodes: list):
        if not arm_nodes:
            return
        if len(arm_nodes) == 1:
            sub = self._build_element_tree(arm_nodes[0])
            sub.parent = alt_element
            alt_element.elements.append(sub)
        else:
            group = Element()
            group.type = ElementType.SECTION
            for n in arm_nodes:
                sub = self._build_element_tree(n)
                sub.parent = group
                group.elements.append(sub)
            group.parent = alt_element
            alt_element.elements.append(group)
