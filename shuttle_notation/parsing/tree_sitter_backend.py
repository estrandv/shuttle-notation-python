from tree_sitter import Language, Parser, Node

from shuttle_notation.parsing.element import Element, ElementType
from tree_sitter_shuttle_notation import language as _shuttle_language


_SHUTTLE_LANG = Language(_shuttle_language())


class TreeSitterBackend:
    def __init__(self):
        self._parser = Parser()
        self._parser.language = _SHUTTLE_LANG
        self._source_lines: list[str] = []

    def parse(self, source_string: str) -> Element:
        self._source_lines = source_string.splitlines(keepends=True)
        tree = self._parser.parse(source_string.encode("utf-8"))
        root = tree.root_node
        return self._build_element_tree(root)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _pos_str(node: Node) -> str:
        return f"({node.start_point.row},{node.start_point.column})"

    def _error_context(self, node: Node, context_chars: int = 40) -> str:
        """Return ~context_chars of source text around the node."""
        row = node.start_point.row
        col = node.start_point.column
        if row < len(self._source_lines):
            line = self._source_lines[row]
            start = max(0, col - context_chars // 2)
            end = min(len(line), col + context_chars // 2)
            snippet = line[start:end].rstrip("\n")
            prefix = "..." if start > 0 else ""
            suffix = "..." if end < len(line) else ""
            return f"{prefix}{snippet}{suffix}"
        return ""

    def _node_snippet(self, node: Node, max_chars: int = 60) -> str:
        """Return up to max_chars of the error node's text."""
        try:
            text = node.text.decode()
            if len(text) > max_chars:
                return text[:max_chars] + "..."
            return text
        except Exception:
            return "<unreadable>"

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
                            f"Malformed section body at {self._pos_str(c)}: "
                            f"{self._node_snippet(c)!r} "
                            f"(context: {self._error_context(c)})"
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
                    f"Malformed input at {self._pos_str(c)}: "
                    f"{self._node_snippet(c)!r} "
                    f"(context: {self._error_context(c)})"
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
                    f"Malformed section body at {self._pos_str(node)}: "
                    f"{self._node_snippet(node)!r} "
                    f"(context: {self._error_context(node)})"
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
                    f"Malformed alternation arm at {self._pos_str(c)}: "
                    f"{self._node_snippet(c)!r} "
                    f"(context: {self._error_context(c)})"
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
