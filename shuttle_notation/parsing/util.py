from shuttle_notation.parsing.element import ElementType
from shuttle_notation.parsing.cursor import Cursor 
import shuttle_notation.parsing.section_parsing as section_parsing
import shuttle_notation.parsing.information_parsing as information_parsing

from decimal import Decimal

# "Business logic" - explain later 
def section_split(source_string) -> list:
    cursor = Cursor(source_string)

    opened_parentheses = 0

    everything = []

    current = ""

    while not cursor.is_done(): 
        match cursor.get():
            case "(": 
                current += cursor.get() 
                opened_parentheses += 1
            case ")":
                current += cursor.get() 
                opened_parentheses -= 1
            case " ":
                if opened_parentheses == 0:
                    if current != "":
                        everything.append(current)
                    current = ""
                else:
                    current += cursor.get()
            case _:
                current += cursor.get()
        cursor.next() 

    if current != "":
        everything.append(current)

    return everything 

class TreeExpander:

    def __init__(self):
        self.tick_list = []

    # Count how many times one would have to use the element to fully expand it and its children. 
    def count_required_alternations(self, element):

        base = 1
        
        if element.type == ElementType.ALTERNATION_SECTION:
            base = len(element.elements)

        # Max of [AC, 1]
        return base * max([self.count_required_alternations(ele) for ele in element.elements] + [1])

    def all_ticked(self, element) -> bool:
        element_ticks = self.get_ticks(element)

        required_ticks = self.count_required_alternations(element) \
            if element.type == ElementType.ALTERNATION_SECTION \
            else 1
        
        children_ok = True 
        for child in element.elements:
            if not self.all_ticked(child):
                children_ok = False

        #print("Ticked", element_ticks, "required", required_ticks)
        
        return element_ticks >= required_ticks and children_ok

    def tree_expand(self, element) -> list:
        full = []

        while not self.all_ticked(element):
            full += self.expand(element, get_repeat(element))

        return full

    # Tick off an element, so that we can count how many times we have done so. 
    # Alternations must be used several times to fully expand, hence the need to count. 
    def tick(self,element):
        self.tick_list.append(element)

    # Returns how many times an element has been ticked so far.
    # Does not account for children.  
    def get_ticks(self, element):
        return len([e for e in self.tick_list if e is element])

    # Expand both alternations and repeats 
    def expand(self, element, repeat) -> list:

        if element.type == ElementType.ATOMIC:
            self.tick(element)
            return duplicate([element], repeat) 
        if element.type == ElementType.SECTION:
            flatmap = []
            for _ in range(0, repeat):
                self.tick(element)
                matrix = [self.expand(e, get_repeat(e)) for e in element.elements]
                for c in matrix:
                    for r in c:
                        flatmap.append(r)
            return flatmap 
        if element.type == ElementType.ALTERNATION_SECTION:

            # Repeat the alternation as required, grabbing the next alternation each time
            full = [] 
            for i in range(0, repeat):
                # Tick element and return amount of times it has been ticked            
                ticks = self.get_ticks(element)
                self.tick(element)
                # Resolve an index from the tick amount (so that, in a 2-len array, 2 follows after 1, 0 after 2, etc)
                mod = ticks % (len(element.elements))
                current_alt = element.elements[mod]
                full += self.expand(current_alt, get_repeat(current_alt))
            return full 

        return []

# Returns the amount of times an element should be repeated, according to its "xN" suffix
def get_repeat(element) -> int:
    information = information_parsing.divide_information(element)
    return information.repetition

# Returns a flat list containing elements copied N times.
def duplicate(elements, times):
    ret = []
    for _ in range(0, times):
        for e in elements:
            ret.append(e)
    return ret 

# Get the information of the element and all its parents, in that order
def get_information_history(element) -> list:
    full_list = []
    current_element = element
    while current_element != None:
        info = information_parsing.divide_information(current_element)
        full_list.append(info)
        current_element = current_element.parent

    return full_list    

# Resolve arguments from the top down of the given element information history. 
# The topmost definition is used as base - args with operations 
#   override the base, args without replace it. 
# TODO: Somewhat overcomplex - including vagrant alias arg
def resolve_full_arguments(
    information_history: list, 
    default_args: dict = {}, # {str:Decimal}, treated as topmost args
    arg_aliases: dict = {} # {str:str}, see parse_args() 
) -> dict:

    all_arg_dicts = []

    # Walk to the top parent, collecting all argument dicts along the way. 
    for info in information_history:
        if info.arg_source != "":
            args = information_parsing.parse_args(info.arg_source, arg_aliases)
            all_arg_dicts.append(args)

    # Append the default args as root 
    dyn_default_args = {}
    for key in default_args:
        dyn_default_args[key] = information_parsing.DynamicArg(default_args[key])
    all_arg_dicts.append(dyn_default_args)

    # Reverse priority order; begin with topmost/root args. 
    all_arg_dicts.reverse()

    # Non-dynamic args; dict of <str,Decimal>
    resolved_args = {}

    for arg_dict in all_arg_dicts:
        for dynamic_arg_key in arg_dict:
            dynamic_arg = arg_dict[dynamic_arg_key]
            # Arg present at a higher level and can be modified 
            if dynamic_arg_key in resolved_args:
                match dynamic_arg.operator:
                    case "*":
                        resolved_args[dynamic_arg_key] *= dynamic_arg.value
                    case "+":
                        resolved_args[dynamic_arg_key] += dynamic_arg.value
                    case "-":
                        resolved_args[dynamic_arg_key] *= dynamic_arg.value
                    case _:
                        # Blank or unknown operator should overwrite
                        resolved_args[dynamic_arg_key] = dynamic_arg.value
            else:
                # Introduce without any operators if no higher level version exists
                resolved_args[dynamic_arg_key] = dynamic_arg.value

    return resolved_args

