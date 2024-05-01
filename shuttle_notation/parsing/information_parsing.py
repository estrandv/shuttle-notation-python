"""

    Parsing related to single-element string-parts. 

"""

from dataclasses import dataclass
from enum import Enum
from decimal import Decimal

from shuttle_notation.parsing.cursor import Cursor
from shuttle_notation.parsing.element import Element, ElementType

"""
    TODO: Discussion on requirements. 
    - Can index be a float?
    - When do we need symbols -instead- of an index? 
    - How do we denote e.g. "mod note number of playing note"? Suffix? Symbol?
        -> Ideally we always have a number, with suffix containing an extra symbol  
    - Should it even be possible to have a suffix without an index? If so, how? 
        -> Possible for section, of course, but not atomic 

"""
@dataclass
class ElementInformation:
    prefix: str = "" # Contents prior to first numeric or special symbol 
    index_string: str = "" # First numeric or special symbol
    suffix: str = "" # Contents after first numeric or special symbol
    repetition: int = 1 # Contents after "*", but before ":"
    arg_source: str = "" # Final contents, after ":"

class InformationPart(Enum):
    PREFIX = 0
    INDEX = 1
    SUFFIX = 2
    REPETITION = 3
    ARGS = 4

def divide_information(element: Element) -> ElementInformation:

    # Initiate with blank defaults 
    information = ElementInformation() 

    # Sections start at suffix; they have no prefix or index 
    current_part = InformationPart.SUFFIX \
        if element.type in [ElementType.SECTION, ElementType.ALTERNATION_SECTION] \
        else InformationPart.PREFIX

    # Return blank when no information string is provided 
    if element.information == "":
        return information

    cursor = Cursor(element.information)

    NUMBERS = "0123456789"

    while True:
        match current_part:
            case InformationPart.PREFIX:
                if not cursor.contains_any(NUMBERS):
                    current_part = InformationPart.SUFFIX
                    # NOTE: Implicit straight-to-suffix on no number
                    # Below is the error we used to throw: 
                    #raise Exception("Malformed input - element information has no index: " + element.information)
                else:
                
                    until_number = cursor.get_until(NUMBERS)
                    information.prefix = until_number

                    # NOTE: Cursor weakness - if first character matches get_until we don't stop "before it" 
                    if cursor.get() not in NUMBERS:
                        cursor.next()

                    current_part = InformationPart.INDEX

            case InformationPart.INDEX:
                information.index_string = cursor.get_until("0123456789", False)
                
                # NOTE: Again, cursor weakness
                if cursor.get() in NUMBERS:
                    cursor.next()

                current_part = InformationPart.SUFFIX
            
            case InformationPart.SUFFIX:

                remaining = cursor.get_remaining() 

                print("Remaining", remaining)

                star_index = remaining.find("*")
                colon_index = remaining.find(":")

                # Since * can appear inside args, we need to check for it before arg declaration 
                star_present = star_index != -1 and (star_index < colon_index or colon_index == -1) 

                if star_present:
                    information.suffix = cursor.get_until("*")
                    cursor.move_past_next("*")
                    current_part = InformationPart.REPETITION
                elif ":" in remaining:
                    information.suffix = cursor.get_until(":")
                    cursor.move_past_next(":")
                    current_part = InformationPart.ARGS
                else:
                    information.suffix = remaining
                    break 

            case InformationPart.REPETITION:
                remaining = cursor.get_remaining() 
                if ":" in remaining:
                    information.repetition = int(cursor.get_until(":"))
                    cursor.move_past_next(":")
                    current_part = InformationPart.ARGS
                elif remaining != "":
                    information.repetition = int(remaining)
                    break 

            case InformationPart.ARGS:
                if not cursor.is_done():
                    information.arg_source = cursor.get_remaining()

                break 

            case _:
                # Shouldn't happen but w/e
                break

    return information

@dataclass
class DynamicArg:
    value: Decimal
    operator: str = ""

# Parse 1.0,arg+2,argb*2.0,argc0.2 [...] part of element info suffix 
# Aliases, provided as {alias:name}, changes <alias> into <name> where
#   keys match. 
def parse_args(arg_source, aliases: dict = {}) -> dict:

    args = {}

    cursor = Cursor(arg_source)
    while True: 
        # Step on separator at a time 
        content = cursor.get_until(",")

        sub_cursor = Cursor(content)
        # Numbers or operators break the key part
        # TODO: Consider ".2" shorthand support 
        non_numeric = sub_cursor.get_until("0123456789+-*")

        # Step into the numeric part of the string unless it began immediately 
        if sub_cursor.peek() != "" and non_numeric != "":
            sub_cursor.next()

        numeric = sub_cursor.get_remaining()

        if numeric != "": 

            num = "".join(numeric[1:]) if numeric[0] in "+-*" else numeric
            sym = numeric[0] if numeric[0] in "+-*" else ""    

            numeric_decimal = Decimal(num)

            new_arg = DynamicArg(numeric_decimal, sym)

            if non_numeric == "":
                if len(args) == 0:
                    # TODO: Some other way to provide this default 
                    # First arg is "time" unless otherwise noted 
                    args["time"] = new_arg
                else:
                    raise Exception("Malformed input: unnamed non-first arg")
            else:
                # Apply alias
                if non_numeric in aliases:
                    non_numeric = aliases[non_numeric]

                args[non_numeric] = new_arg

        cursor.move_past_next(",")
        if cursor.is_done():
            break 

    return args 

