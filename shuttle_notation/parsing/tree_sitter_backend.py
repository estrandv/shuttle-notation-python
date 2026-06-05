import ctypes
import os
import subprocess
import tempfile
from pathlib import Path

from tree_sitter import Language, Parser, Node

from shuttle_notation.parsing.element import Element, ElementType

_PARSER_DIR = Path(__file__).resolve().parent.parent.parent
_GRAMMAR_DIR = Path(__file__).resolve().parent.parent.parent.parent / "tree-sitter-shuttle-notation"
_SRC_DIR = _GRAMMAR_DIR / "src"
_SO_PATH = _PARSER_DIR / "shuttle_notation" / "shuttle.so"


def _build_shared_lib():
    if _SO_PATH.exists():
        return str(_SO_PATH)
    result = subprocess.run(
        [
            "cc", "-shared", "-fPIC", "-o", str(_SO_PATH),
            str(_SRC_DIR / "parser.c"),
            f"-I{_SRC_DIR}",
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

    def _build_element_tree(self, cst_node: Node) -> Element:
        element = Element()
        element.parent = None

        match cst_node.type:
            case "root":
                children = [c for c in cst_node.children if c.type in ("note", "section")]
                if not children:
                    element.type = ElementType.SECTION
                    return element
                if len(children) == 1:
                    return self._build_element_tree(children[0])
                element.type = ElementType.SECTION
                for child in children:
                    sub = self._build_element_tree(child)
                    sub.parent = element
                    element.elements.append(sub)

            case "note":
                element.type = ElementType.ATOMIC
                element.information = cst_node.text.decode()

            case "section":
                element.type = ElementType.SECTION
                body_children = []
                trailing_parts = []
                after_paren = False
                for c in cst_node.children:
                    if c.type == ")":
                        after_paren = True
                    elif c.type in ("(", ")"):
                        pass
                    elif after_paren:
                        trailing_parts.append(c)
                    else:
                        body_children.append(c)

                self._process_section_body(element, body_children)

                if trailing_parts:
                    element.information = "".join(c.text.decode() for c in trailing_parts)
                else:
                    element.information = ""

            case "alternation":
                element.type = ElementType.ALTERNATION_SECTION
                self._process_alternation(element, cst_node)

            case _:
                pass

        return element

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

    def _process_alternation(self, alt_element: Element, cst_node: Node):
        current_arm = []
        for c in cst_node.children:
            if c.type == "/":
                self._flush_arm(alt_element, current_arm)
                current_arm = []
            elif c.type in ("note", "section"):
                current_arm.append(c)

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
