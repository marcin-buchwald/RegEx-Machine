import unicodedata

import unicode
import unicodedata2


class NFA:
    """Non Final State Automata class.
    Contains list of all states, i.e. nodes of the NFA graph"""

    def __init__(self):
        self.node_list = []
        self.start_node = None
        self.end_node = None

        self.max_match_group_no = 0  # values: numbers, e.g. 1, 2, 3

    def add_node(self, node):
        self.node_list.append(node)

    def node_labels(self):
        return [n.state_label for n in self.node_list]

    def print_graph(self):
        for node in self.node_list:
            print(node.to_string())
            print(node.output_states_to_string())

    def edges(self):
        ret = [("Start", self.node_list[0].state_label)]

        for node in self.node_list:
            output_states = []
            if node.output_states is not None:
                output_states += node.output_states
            if node.loop_back_output_states is not None:
                output_states += node.loop_back_output_states
            if node.state_type == "repetition" and node.loop_output_states is not None:
                output_states += node.loop_output_states

            ret += list(zip([node.state_label] * len(output_states), [n.state_label for n in output_states]))
        print(ret)
        return ret


class State:
    """Generic state node of NFA, used for string matching and as a base for other specialized states"""

    def __init__(self, state_type, state_label, match_values, output_states):

        # state_type:
        # Matching states:
        # - string match (e.g Marcin)
        # - multi match (e.g [^A-D] \s [a-z]
        # - match all (.)
        # - match group (named group, tbd)
        # Empty states (for structure):
        # - expression (any expression in round brackets)
        # - choice (e.g xxx|yyy)
        # - repetition (e.g * + {1, 2}
        self.state_type = state_type

        # state_label, example of values:
        # for state_type: string match: "Marcin", "Tree", "email: "
        # for state_type: multi match: ".", "\s", [a-z], [a-zA-Z123]
        self.state_label = state_label

        # match_values is a list
        # examples:
        # for state_type: string match: ["Marcin] or ["Tree"]
        # for state_type: multi match: [" ", "\n", "\t", "\v"], ["a", "b", "c", ..., "z"]
        self.match_values = match_values

        # output states list, contains State objects
        # graph traversal is performed by invoking
        # - State.is_matched(text, start_position) for each member of the list
        # - start_position is the position directly after the text already matched
        # - moving to all the states that return True
        self.output_states = output_states

        # this output is a special table for recurrent states, going though this edge will not reset repetition counter
        # the r -> (*) is rep_output_state edge, doesn't reset rep counter in the (*)
        #
        #  X -------> (*) ----->
        #              ^    |
        #              |    |
        #              R __\/
        self.loop_back_output_states = []

        self.match_group_start = []  # values: list of match group names that start here, e.g ["match_1", "match_2"]
        self.match_group_end = []  # values: list or match groups names that end here, e.g. ["match_1", "match_4"]

    def to_string(self):
        """Returns a string containing important information about the state"""
        ret = self.state_type + ": " + self.state_label

        match_group_ret = ""
        for match_group in self.match_group_start:
            match_group_ret += " " + str(match_group)
        if len(match_group_ret) > 0:
            ret += "\n    match groups start: " + match_group_ret

        match_group_ret = ""
        for match_group in self.match_group_end:
            match_group_ret += " " + str(match_group)
        if len(match_group_ret) > 0:
            ret += "\n    match groups end: " + match_group_ret

        return ret

    def output_states_to_string(self):
        ret = ""
        for state in self.output_states:
            ret += "    >" + state.to_string() + "\n"

        for state in self.loop_back_output_states:
            ret += "  lb>" + state.to_string() + "\n"

        return ret

    def is_matched(self, text, position):
        """Returns True if the text is matched at the given position, the second return value is length of the match
        If there's no match, the method returns False, 0"""
        if position + len(self.match_values[0]) > len(text):
            return False, 0

        match = text[position:position + len(self.match_values[0])] == self.match_values[0]
        return match, len(self.match_values[0]) if match else 0


class EndState(State):
    """End state indicates end of state machine, one per NFA"""

    def __init__(self):
        super().__init__("end", "end", None, None)

    def is_matched(self, text, position):
        return True, 0

    def output_states_to_string(self):
        return ""


class MultiMatchState(State):
    """MultiMatchState handles
    *    [] syntax, inclusive ranges, like a-z
    *    . (match all)
    *    \\s (match whitespace)
    *    \\w (match word characters)
    *    \\d (match digit)
    """

    def __init__(self, state_label, match_values, output_states):
        super().__init__("multi match", state_label, match_values, output_states)

    # range is: [a-z]
    def add_range(self, range_str):
        if len(range_str) < 3 or range_str[1] != "-":
            return False

        self.match_values += [chr(x) for x in range(ord(range_str[0]), ord(range_str[2]) + 1)]
        return True

    # digit, word (digit, letter, underscore), white space is: \d \w \s
    def add_multi(self, multi_str):
        if multi_str in "d":
            self.match_values += [chr(x) for x in range(ord("0"), ord("9") + 1)]
            return True

        if multi_str in "w":
            self.match_values += [chr(x) for x in range(ord("0"), ord("9") + 1)]
            self.match_values += [chr(x) for x in range(ord("a"), ord("z") + 1)]
            self.match_values += [chr(x) for x in range(ord("A"), ord("Z") + 1)]
            self.match_values.append("_")
            return True

        if multi_str in "s":
            self.match_values += [" ", "\n", "\t", "\r"]
            return True

        return False

    def is_matched(self, text, position):
        if position >= len(text):
            return False, 0
        match = text[position] in self.match_values
        return match, 1 if match else 0


class MultiMatchUnicodeState(State):
    """MultiMatchUnicodeState handles
    *    unicode categories like L, Lo, etc
    *    unicode groups with full names, like Letters, Other_Letters, etc
    *    TODO: integrate with non-unicode multi match
    """

    def __init__(self, state_label, match_value, output_states, is_negative):
        super().__init__("u-multi match", state_label, [], output_states)
        self.is_negative = is_negative

        # possible match types:
        # * category
        # * block
        # * script
        match_type = unicode.name_to_type[match_value]
        if match_type == "long category":
            self.match_values = unicode.category_hierarchy[unicode.long_to_short_category[match_value]]
            self.match_type = "short subcategory"
        elif match_type == "long subcategory":
            self.match_values[0] = unicode.long_to_short_category[match_value]
            self.match_type = "short subcategory"
        elif match_type == "short category":
            self.match_values = unicode.category_hierarchy[match_value]
            self.match_type = "short subcategory"
        else:
            self.match_values = [match_value]
            self.match_type = match_type

    def is_matched(self, text, position):
        if position >= len(text):
            return False, 0
        if self.match_type == "short subcategory":
            if (not self.is_negative and unicodedata.category(text[position]) in self.match_values) or \
                    (self.is_negative and unicodedata.category(text[position]) not in self.match_values):
                return True, 1
            else:
                return False, 0
        elif self.match_type == "block":
            if (not self.is_negative and
                    unicode.unicode_blocks[self.match_values[0]][0] <= ord(text[position])
                    <= unicode.unicode_blocks[self.match_values[0]][1]) or\
                    (self.is_negative and
                     not (unicode.unicode_blocks[self.match_values[0]][0] <= ord(text[position])
                          <= unicode.unicode_blocks[self.match_values[0]][1])):
                return True, 1
            else:
                return False, 0
        elif self.match_type == "script":
            if (not self.is_negative and unicodedata2.script(text[position]) in self.match_values) or \
                    (self.is_negative and unicodedata2.script(text[position]) not in self.match_values):
                return True, 1
            else:
                return False, 0
        else:
            return False, 0


class NegativeMultiMatchState(MultiMatchState):
    """This state handles negative matches, that is: [^...] syntax. It's based on MultiMatchState and simply negates its
    is_match value.
    """

    def __init__(self, state_label, match_values, output_states):
        super().__init__(state_label, match_values, output_states)
        self.state_label = "neg multi match"

    def is_matched(self, text, position):
        if position >= len(text):
            return False, 0
        match = text[position] not in self.match_values
        return match, 1 if match else 0


class MatchAllState(State):
    def __init__(self, state_label, output_states):
        super().__init__("match all", state_label, None, output_states)

    def is_matched(self, text, position):
        if position >= len(text):
            return False, 0
        return True, 1


class RecurringState(State):
    """The state represents repetitions (loops) like *, +, {m,m}
    It has additional output array: loop_output_states that leads to nodes connected in the loop directly to it.
    This is how recurrent node is connected:

    (prev node)-output_states->-----------------------(rec node)--------------------------------------|--output_states->
                               ^                                                                      |
                               |--<--loop_back_output_states---(looped nodes)--<--loop_output_states--|

    loop_output_states and loop_back_output_states are there for repetition counting and making sure rep count is in
    range (min_rep, max_rep)
    Each time interpreter goes though an edge from loop_back_output_states, it updates rep counter (+1).
    If the interpreter goes though output_states edge to the rec node, the rep counter is set to 1.
    This way nested loops work correctly.
    If rep counter is below min_rep, the edges from output_states of rec node are not used.
    If rep counter is above max_rep, the edges from loop_output_states of rec node are not used.
    """

    def __init__(self, state_label, loop_output_states, min_rep, max_rep):
        self.min_rep = min_rep
        self.max_rep = max_rep
        self.loop_output_states = loop_output_states

        super().__init__("repetition", state_label, None, [])

    def is_matched(self, text, position):
        # repetition and choice are states without match values, they simply let the interpreter enter them
        # than the interpreter iterates over output states to check if any of them match
        return True, 0

    def output_states_to_string(self):
        ret = ""
        for state in self.output_states:
            ret += "    >" + state.to_string() + "\n"

        for state in self.loop_back_output_states:
            ret += "  lb>" + state.to_string() + "\n"

        for state in self.loop_output_states:
            ret += "   L>" + state.to_string() + "\n"

        return ret


class ExpressionState(State):
    """top level state: represents a choice "|" """

    def __init__(self, state_label, output_states):
        super().__init__("expression", state_label, None, output_states)

    def is_matched(self, text, position):
        # repetition and choice are states without match values, they simply let the interpreter enter them
        # than the interpreter iterates over output states to check if any of them match
        return True, 0


class BackReferenceState(State):
    """State representing back references to match groups, e.g. \\1, \\2, ..., \\99"""

    def __init__(self, state_label, ref_no, output_states):
        super().__init__("back reference", state_label, None, output_states)
        self.ref_no = ref_no

    def is_matched(self, text, position, reference):
        if reference is None:
            return False, 0

        if position + len(reference) > len(text):
            return False, 0

        match = text[position:position + len(reference)] == reference
        return match, len(reference) if match else 0


class BoundaryState(State):
    """state representing boundaries, like beginning or end of text, words, lines, etc"""

    boundary_mapping = {
        "^": "start text or line",
        "$": "end text or line",
        "b": "word boundary",
        "A": "start text",
        "Z": "end text"
    }

    def __init__(self, state_label, boundary_type, output_states):
        super().__init__("anchor", state_label, None, output_states)
        self.boundary_type = BoundaryState.boundary_mapping[boundary_type]

    def is_matched(self, text, position):
        if position == len(text):
            if self.boundary_type in ["end text", "end text or line", "word boundary"]:
                return True, 0
            else:
                return False, 0

        if self.boundary_type == "start text":
            return position == 0, 0

        if self.boundary_type == "end text":
            return position == len(text) - 1, 0

        if self.boundary_type == "start text or line":
            if position > 0 and text[position - 1] in "\n\r":
                return True, 0
            return position == 0, 0

        if self.boundary_type == "end text or line":
            # check for end of line, end of text is handled above along with other types of text end types
            if position < len(text):
                return text[position] in "\n\r", 0

        if self.boundary_type == "word boundary":
            non_word_chars = " \t\n\r.,;:?!-><\\()/"

            # print("position:", position, ", len:", len(text))
            if text[position] not in non_word_chars and (
                    position == len(text) - 1 or text[position + 1] in non_word_chars):
                return True, 0
            if text[position] not in non_word_chars and (position == 0 or text[position - 1] in non_word_chars):
                return True, 0
            if text[position] in non_word_chars and (
                    position == len(text) - 1 or text[position + 1] not in non_word_chars):
                return True, 0
            if text[position] in non_word_chars and (position == 0 or text[position - 1] not in non_word_chars):
                return True, 0

        return False, 0
