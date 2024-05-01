"""

Parsing logic related to "()"-sections, "/"-alternation and "x"-repetition. 

"""

import util 
from cursor import Cursor
from element import Element, ElementType
import json 
import pytest 

# Divides string into Elements, arranged in a tree structure
#   as dictated by section syntax. 
def build_tree(source_string) -> Element:
    
    current_element = Element()
    current_element.type = ElementType.SECTION 

    def store(element):
        if current_element.type == ElementType.ALTERNATION_SECTION:
            current_alternation.append(element)
        else:
            current_element.elements.append(element)
            element.parent = current_element

    def end_current_alternation(alternation):

        if len(alternation) > 1:
            sub_section = current_element.add()
            sub_section.type = ElementType.SECTION
            
            for ele in alternation:
                ele.parent = sub_section
                sub_section.elements.append(ele)
        else:
            # Looped to be 0-len safe, although typically one element 
            for ele in alternation:
                ele.parent = current_element
                current_element.elements.append(ele)


    # Divide into substrings, separated by space unless bracketed
    # Dealing with one bracket-layer at a time 
    current_alternation = []
    for substring in util.section_split(source_string):

        if "(" in substring or ")" in substring:

            # Grab meta-information and then recursively parse bracketed sections 

            if substring[0] != "(":
                raise Exception("Malformed input - section does not start with '(' :" + substring)

            # TODO: Suffix should be allowed to contain ")" - we should not look for the last index
            #   but for the index of when all parentheses have been closed. 
            end_index = substring.rfind(")")

            if end_index == -1:
                raise Exception("Malformed input - section does not have an ending ')': " + substring)

            # Perform information gathering 
            end_information = "".join(substring[end_index + 1:]) if substring[-1] != ")" else ""

            unwrap = "".join(substring[1:end_index])

            sub_section = build_tree(unwrap)
            sub_section.information = end_information
            store(sub_section)

        elif substring == "/":

            if current_element.type == ElementType.ALTERNATION_SECTION:

                if len(current_alternation) == 0:
                    raise Exception("Malformed input - possible duplicate '/':")

                # Not the first encountered / 
                # Take all elements created since the last /
                # Add them as a section if multiple 
                
                end_current_alternation(current_alternation) 
                current_alternation = []

            elif len(current_element.elements) > 0: 
                # Classify ongoing section as alternation
                # Move any previously passed elements into a subsection (if plural)
                current_element.type = ElementType.ALTERNATION_SECTION
                current_alternation = []
                
                if len(current_element.elements) > 1:
                    port = current_element.elements 
                    sub_section = Element()
                    sub_section.type = ElementType.SECTION
                    sub_section.elements = port
                    for e in sub_section.elements:
                        e.parent = sub_section
                    current_element.elements = [sub_section]
                    
            else:
                raise Exception("Malformed input - '/' written before any other elements in section")
        else:
            # Regular, atomic entry 
            atomic = Element() 
            atomic.type = ElementType.ATOMIC
            atomic.information = substring

            store(atomic)

    # In case last element is part of an alternation (post-/)
    end_current_alternation(current_alternation)
    current_alternation = []
    
    return current_element
