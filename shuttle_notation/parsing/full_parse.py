import shuttle_notation.parsing.information_parsing as information_parsing
import shuttle_notation.parsing.section_parsing as section_parsing
from shuttle_notation.parsing.element import Element, ElementType, ResolvedElement
import shuttle_notation.parsing.util as util
 
from dataclasses import dataclass
from decimal import Decimal

class Parser:
    def __init__(self):
        # provided as alias:realname
        self.arg_aliases = {}
        self.arg_defaults = {}

    def parse(self, source_string: str) -> list[ResolvedElement]:
        # Run the whole intended sequence of parsing, from source to final elements 
        top_element = section_parsing.build_tree(source_string)
        tree = util.TreeExpander() 
        sequence = tree.tree_expand(top_element)
        return [self.resolve(e) for e in sequence]

    def resolve(self, element: Element) -> ResolvedElement:
        
        match element.type:
            case ElementType.ATOMIC:
                info = information_parsing.divide_information(element)
                history = util.get_information_history(element)
                args = util.resolve_full_arguments(
                    history, self.arg_defaults, self.arg_aliases
                )
                
                resolved = ResolvedElement(
                    info.prefix, 
                    int(info.index_string) if info.index_string != "" else 0,  
                    info.suffix, 
                    args
                )
                return resolved 

            case _:
                raise Exception("Only ATOMIC elements can be resolved!")

