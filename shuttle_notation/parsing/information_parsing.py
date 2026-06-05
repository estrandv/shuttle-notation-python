from dataclasses import dataclass
from enum import Enum
from decimal import Decimal
import re

from shuttle_notation.parsing.element import Element, ElementType

@dataclass
class ElementInformation:
    prefix: str = ""
    index_string: str = ""
    suffix: str = ""
    repetition: int = 1
    arg_source: str = ""

class InformationPart(Enum):
    PREFIX = 0
    INDEX = 1
    SUFFIX = 2
    REPETITION = 3
    ARGS = 4

_ATOMIC_RE = re.compile(r'^([a-zA-Z_]*)(\d+)(.*?)(?:\*(\d+))?(?::(.*))?$')
_SECTION_RE = re.compile(r'^(.*?)(?:\*(\d+))?(?::(.*))?$')

def divide_information(element: Element) -> ElementInformation:
    info = ElementInformation()
    text = element.information
    if not text:
        return info

    is_section = element.type in (ElementType.SECTION, ElementType.ALTERNATION_SECTION)
    has_index = not is_section and bool(re.search(r'\d', text.split(":")[0]))

    if has_index:
        m = _ATOMIC_RE.match(text)
        info.prefix = m.group(1) or ""
        info.index_string = m.group(2) or ""
        info.suffix = m.group(3) or ""
        if m.group(4):
            info.repetition = int(m.group(4))
        info.arg_source = m.group(5) or ""
    else:
        m = _SECTION_RE.match(text)
        info.suffix = m.group(1) or ""
        if m.group(2):
            info.repetition = int(m.group(2))
        info.arg_source = m.group(3) or ""

    return info

@dataclass
class DynamicArg:
    value: Decimal
    operator: str = ""
    other_arg_reference: str = ""

_ARG_RE = re.compile(r'^([^0-9+*=-]*)([-+*=]?)([\d.]+)([a-zA-Z]+)?$')

def parse_args(arg_source, aliases={}):
    args = {}
    for part in arg_source.split(","):
        if not part:
            continue
        m = _ARG_RE.match(part)
        if not m:
            raise Exception(f"Malformed arg: {part}")
        key = m.group(1)
        op = m.group(2) or ""
        num_str = m.group(3)
        ref = m.group(4) or ""
        value = Decimal(num_str)
        arg = DynamicArg(value, op, ref)
        if not key:
            if not args:
                args["time"] = arg
            else:
                raise Exception("Malformed input: unnamed non-first arg")
        else:
            key = aliases.get(key, key)
            args[key] = arg
    return args
