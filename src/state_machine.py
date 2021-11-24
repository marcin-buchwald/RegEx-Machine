class NSA:
    def __init__(self):
        self.node_list = []
        self.start_node = None
        self.end_node = None

        self.max_match_group_no = -1  # values: numbers, e.g. 1, 2, 3

    def add_node(self, node):
        self.node_list.append(node)

    def node_labels(self):
        return [n.state_label for n in self.node_list]

    def edges(self):
        ret = [("Start", self.node_list[0].state_label)]

        for node in self.node_list:
            output_states = []
            if node.output_states is not None:
                output_states += node.output_states
            if node.loop_back_output_states is not None:
                output_states += node.loop_back_output_states
            if node.state_type == "recurrence" and node.loop_output_states is not None:
                output_states += node.loop_output_states

            ret += list(zip([node.state_label] * len(output_states), [n.state_label for n in output_states]))
        print(ret)
        return ret


class State:
    def __init__(self, state_type, state_label, match_values, output_states):

        # state_type:
        # Matching states:
        # - string match (e.g Marcin)
        # - multi match (e.g [^A-D] \s [a-z]
        # - match all (.)
        # - match group (named group, tbd)
        # Emty states (for structure):
        # - expression (any expression in round brackets)
        # - choice (e.g xxx|yyy)
        # - recurrence (e.g * + {1, 2}
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
        # - recurrence is performed by invoking self.is_matched(text, start_position)
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
        ret = self.state_type + " " + self.state_label
        for match_group in self.match_group_start:
            ret += " Start match group " + str(match_group)
        for match_group in self.match_group_end:
            ret += " End match group " + str(match_group)

        return ret

    def output_states_to_string(self):
        ret = ""
        for state in self.output_states:
            ret += "    >" + state.to_string() + "\n"

        for state in self.loop_back_output_states:
            ret += "  lb>" + state.to_string() + "\n"

        return ret

    def is_matched(self, text, position):
        # if self.state_type == "string match":
        if position + len(self.match_values[0]) > len(text):
            return False, 0

        match = text[position:position + len(self.match_values[0])] == self.match_values[0]
        return match, len(self.match_values[0]) if match else 0


class EndState(State):
    def __init__(self):
        super().__init__("end", "end", None, None)

    def is_matched(self, text, position):
        return True, 0

    def output_states_to_string(self):
        return ""


class MultiMatchState(State):
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


class MatchAllState(State):
    def __init__(self, state_label, output_states):
        super().__init__("match all", state_label, None, output_states)

    def is_matched(self, text, position):
        if position >= len(text):
            return False, 0
        return True, 1


class NegativeMultiMatchState(MultiMatchState):
    def __init__(self, state_label, match_values, output_states):
        super().__init__(state_label, match_values, output_states)
        self.state_label = "negative multi match"

    def is_matched(self, text, position):
        if position >= len(text):
            return False, 0
        match = text[position] not in self.match_values
        return match, 1 if match else 0


# how to handle recurrence?
# for * that is {0, } it's easy, output 0: recurrence, output 1: go forward, no need to keep a count of recurrence
# + =  {1, } or more general {m, n} there n >= m >= 0, two approaches:
# - produce a state machine for every needed occurence (1 for +, m for {m, n})
#   combine them in a chain and add recurrence state at the end
#   This blows up the graph, but also simplifies traversal
#   But how to handle {min, max} repetition? Example of s {4, 7}
#
#   s1-->--s2-->--s3-->--s4-->-+->--------------------------------|
#                              |                                  v
#                              +-->--s5--+-->---------------------|
#                                        |                        v
#                                        +-->--s6--+-->-----------+-->-
#                                                  |              ^
#                                                  +-->--s7-->----|
#
# - make sure state machine interpreter handles repetitions, that is keeps a counter of occurences and
#   performs matches looping the state until m occurences is reached, only after exceeding the threshhold
#   the interpreter is allowed to move to another state
#   State needs to keep the min_rep and max_rep fields to the interpreter
class RecurringState(State):
    def __init__(self, state_label, loop_output_states, min_rep, max_rep):
        self.min_rep = min_rep
        self.max_rep = max_rep
        self.loop_output_states = loop_output_states

        super().__init__("recurrence", state_label, None, [])

    def is_matched(self, text, position):
        # recurrence and choice are states without match values, they simply let the interpreter enter them
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


# top level state: represents a choice "|"
class ExpressionState(State):
    def __init__(self, state_label, output_states):
        super().__init__("expression", state_label, None, output_states)

    def is_matched(self, text, position):
        # recurrence and choice are states without match values, they simply let the interpreter enter them
        # than the interpreter iterates over output states to check if any of them match
        return True, 0


# top level state: represents a choice "|"
class BackReferenceState(State):
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
