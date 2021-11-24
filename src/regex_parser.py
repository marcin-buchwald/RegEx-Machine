from state_machine import State, MatchAllState, MultiMatchState, RecurringState, EndState, ExpressionState, NSA, \
    NegativeMultiMatchState, BackReferenceState
from tokenizer import Tokenizer


class RegExParser:
    def __init__(self, regex_pattern):
        self.tokenizer = Tokenizer(regex_pattern)
        self.current_token = ("empty", None)
        self.verbose = 1
        self.group_list = []
        self.rec_list = []
        self.nsa = NSA()

    def next_token(self):
        self.current_token = self.tokenizer.get_next_token()
        if self.verbose > 2:
            print("current token", self.current_token)

    def print_error(self, text):
        if self.verbose > 0:
            print("parse error at position: ", self.tokenizer.position, ", message: ", text, ", current token: ",
                  self.current_token)

    def print_log(self, text):
        if self.verbose > 1:
            print(text)

    def debug_decorator(func):
        verbose = 0

        def wrapper(*args, **kwargs):
            if verbose > 0:
                print(func.__name__ + " ((")

            ret = func(*args, **kwargs)

            if verbose > 0:
                print(")) " + func.__name__)

            return ret

        return wrapper

    # 'atom' = -->-+->--[characters]-->---------------------------------+
    #             |                                                    |
    #             +->--[.]---------->----------------------------------+
    #             |                                                    |
    #             +->-[(]-->--[expression]-->--[)]-->------------------+->-
    #             |                                                    |
    #             +->-[[]-->--[characterclass]-->--[]]-->--------------+
    #             |                                                    |
    #             +->-[[]-->--[~]-->--[characterclass]-->--[]]-->------+
    #
    def atom(self):
        if self.current_token[0] in ["string", "hex", "oct"]:
            state = State("string match", "string_" + self.current_token[1], [self.current_token[1]], [])
            self.nsa.add_node(state)
            self.next_token()
            return True, state, [state]

        if self.current_token[0] in ["back reference"]:
            state = BackReferenceState("back_ref_" + self.current_token[1], self.current_token[1], [])
            self.nsa.add_node(state)
            self.next_token()
            return True, state, [state]

        if self.current_token[0] in ["escaped"]:
            if self.current_token[1] in "swd":
                state = MultiMatchState("multi match: whitespace", [], [])
                state.add_multi(self.current_token[1])
                self.nsa.add_node(state)
                self.next_token()
                return True, state, [state]
            else:
                state = State("esc string match", "string_" + self.current_token[1], [self.current_token[1]], [])
                self.nsa.add_node(state)
                self.next_token()
                return True, state, [state]

        if self.current_token == ("meta", "."):
            self.next_token()
            state = MatchAllState(".", [])
            self.nsa.add_node(state)
            return True, state, [state]

        if self.current_token == ("meta", "("):
            # register a match group
            self.nsa.max_match_group_no += 1
            max_match_group_no = self.nsa.max_match_group_no

            self.next_token()

            result, expression_state, expression_state_output = self.expression()
            if not result:
                return False, None, None

            if self.current_token == ("meta", ")"):
                # add match group
                # first check for a type of expression in ()
                # if it's recurrence, we need to add a new state to handle the match group
                if expression_state.state_type == "recurrence":
                    match_state = ExpressionState("match group state", [expression_state])
                    self.nsa.add_node(match_state)
                    expression_state = match_state

                expression_state.match_group_start += [max_match_group_no]
                for state in expression_state_output:
                    state.match_group_end += [max_match_group_no]

                self.next_token()
                return True, expression_state, expression_state_output
            else:
                self.print_error("Atom: expected \")\"")
                return False, None, None

        if self.current_token == ("meta", "["):
            self.next_token()

            negative_range = False
            if self.current_token == ("meta", "^"):
                negative_range = True
                self.next_token()

            if self.current_token[0] != "setelement" and self.current_token[0] != "escaped setelement" and \
                    self.current_token[0] != "range setelement":
                self.print_error("Atom: expected set element")
                return False, None, None

            match = self.current_token[1]
            if negative_range:
                multiMatchState = NegativeMultiMatchState("neg multi match: " + match, [], [])
            else:
                multiMatchState = MultiMatchState("multi match: " + match, [], [])
            if self.current_token[0] == "range setelement":
                multiMatchState.add_range(match)
            elif self.current_token[0] == "escaped setelement":
                multiMatchState.add_multi(match)
            else:
                multiMatchState.match_values.append(match)
            self.nsa.add_node(multiMatchState)
            self.next_token()

            while self.current_token != ("meta", "]"):
                if self.current_token[0] != "setelement" and self.current_token[0] != "escaped setelement" and \
                        self.current_token[0] != "range setelement":
                    self.print_error("Atom: expected set element")
                    return False, None, None

                if self.current_token[0] == "range setelement":
                    multiMatchState.add_range(self.current_token[1])
                    multiMatchState.state_label += self.current_token[1]
                elif self.current_token[0] == "escaped setelement":
                    multiMatchState.add_multi(self.current_token[1])
                    multiMatchState.state_label += self.current_token[1]
                else:
                    multiMatchState.match_values.append(self.current_token[1])
                    multiMatchState.state_label += self.current_token[1]

                self.next_token()

            self.next_token()
            return True, multiMatchState, [multiMatchState]

        if self.current_token in [("meta", "|"), ("meta", ")")]:
            return True

        self.print_error("Atom: end of atom reached, not interpretation for current token")
        return False, None, None

    atom = debug_decorator(atom)

    # 'factor' = -->-+->--[atom]-->-------------------+
    #               |                                |
    #               |                                |
    #               +->--[atom]->-[metacharacters]->-+->--
    def factor(self):
        output_states = []
        result, atom_state, output_states = self.atom()
        if not result:
            return False, None, None

        if self.current_token == ("end", None):
            return True, atom_state, output_states

        if self.current_token in [("meta", "+"), ("meta", "*"), ("meta", "?"), ("meta", "{")]:

            min_rep, max_rep = 1, 1
            rep_label = self.current_token[1]

            if self.current_token == ("meta", "+"):
                min_rep, max_rep = 1, 999999
            if self.current_token == ("meta", "*"):
                min_rep, max_rep = 0, 999999
            if self.current_token == ("meta", "?"):
                min_rep, max_rep = 0, 1

            # {m}
            # {,n}
            # {m,}
            # {m,n}
            if self.current_token == ("meta", "{"):
                self.next_token()

                # {m
                if self.current_token[0] == "string":
                    if not self.current_token[1].isnumeric():
                        self.print_error("a number expected")
                        return False, None, None
                    min_rep = int(self.current_token[1])
                    rep_label += self.current_token[1]
                    self.next_token()

                    # {m,
                    if self.current_token == ("meta", ","):
                        rep_label += self.current_token[1]
                        self.next_token()

                        # {m,n}
                        if self.current_token[0] == "string":
                            if not self.current_token[1].isnumeric():
                                self.print_error("a number expected")
                                return False, None, None
                            max_rep = int(self.current_token[1])
                            rep_label += self.current_token[1]
                            self.next_token()
                            if self.current_token == ("meta", "}"):
                                pass
                                # self.next_token()
                            else:
                                self.print_error("} expected")
                                return False, None, None
                        # {m,}
                        elif self.current_token == ("meta", "}"):
                            max_rep = 999999
                        else:
                            self.print_error("} expected")
                            return False, None, None
                    # {m}
                    elif self.current_token == ("meta", "}"):
                        max_rep = min_rep
                        # self.next_token()
                    else:
                        self.print_error(", or } expected")
                        return False, None, None
                # {,n}
                elif self.current_token == ("meta", ","):
                    min_rep = 0
                    rep_label += self.current_token[1]
                    self.next_token()
                    if self.current_token[0] == "string":
                        if not self.current_token[1].isnumeric():
                            self.print_error("a number expected")
                            return False, None, None
                        max_rep = int(self.current_token[1])
                        rep_label += self.current_token[1]
                        self.next_token()
                        if self.current_token == ("meta", "}"):
                            pass
                            # self.next_token()
                        else:
                            self.print_error("} expected")
                            return False, None, None
                    else:
                        self.print_error(", n} expected")
                        return False, None, None
                else:
                    self.print_error("{m, n} expected")
                    return False, None, None

                rep_label += self.current_token[1]

            recurring_state = RecurringState("Rec_" + rep_label + "_" + str(len(self.rec_list)), [atom_state], min_rep,
                                             max_rep)
            self.nsa.add_node(recurring_state)
            self.rec_list += [recurring_state]

            for out_state in output_states:
                out_state.loop_back_output_states.append(recurring_state)

            self.next_token()
            return True, recurring_state, [recurring_state]

        return True, atom_state, output_states

    factor = debug_decorator(factor)

    # 'term' = -->-+->--[factor]-->----------+
    #             |                         |
    #             |                         |
    #             +->--[factor]->-[term]-->-+->--
    def term(self):
        result, state, output_states = self.factor()
        if not result:
            return False, None, None

        while self.current_token != ("end", None) and self.current_token not in [("meta", "|"), ("meta", ")")]:
            result, next_factor, next_output_states = self.factor()
            if not result:
                return False, None, None

            for out_st in output_states:
                out_st.output_states.append(next_factor)

            output_states = next_output_states

        return True, state, output_states

    term = debug_decorator(term)

    # 'expression' = -->-+->--[term]---->--------------------+
    #                   |                                   |
    #                   |                                   |
    #                   +->--[term]->-[|]->-[expression]-->-+->--
    def expression(self):
        result, state, output_states = self.term()
        if not result:
            return False, None, None

        if self.current_token == ("end", None):
            end_state = EndState()
            self.nsa.add_node(end_state)
            for out_st in output_states:
                out_st.output_states.append(end_state)
            return True, state, output_states

        expression_state = None
        if self.current_token == ("meta", "|"):
            expression_state = ExpressionState("EXP", [state])
            self.nsa.add_node(expression_state)

        while self.current_token == ("meta", "|"):
            self.next_token()

            result, next_term, next_output_states = self.term()
            if not result:
                return False, None, None

            expression_state.output_states.append(next_term)
            output_states += next_output_states

        if self.current_token not in [("end", None), ("meta", ")")]:
            self.print_error("Expression: end of expression reached")
            return False, None, None

        if self.current_token == ("end", None):
            end_state = EndState()
            self.nsa.add_node(end_state)
            for out_st in output_states:
                out_st.output_states.append(end_state)
            output_states = None

        return True, state if expression_state is None else expression_state, output_states

    expression = debug_decorator(expression)

    def parse(self):

        self.next_token()

        result, expression, output_state = self.expression()
        if not result:
            return False, None
        return self.current_token == ("end", None), expression

