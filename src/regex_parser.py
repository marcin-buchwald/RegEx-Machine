from state_machine import State, MatchAllState, MultiMatchState, RecurringState, EndState, ExpressionState, NFA, \
    NegativeMultiMatchState, BackReferenceState, BoundaryState, MultiMatchUnicodeState
from tokenizer import Tokenizer
import codecs


class RegExParser:
    """
    Parses a reg-exp pattern and creates NFA graph.

    Each of the following method parses a part of the reg-ex pattern, with top one being 'expression'
    atom
    factor
    term
    expression

    Each of the above methods returns a triplet:
    * success flag (True / False)
    * node representing left-most elements of the parsed part of the graph (part's input)
    * list of right-most elements of the parsed part of the graph (part's output)
    """
    def __init__(self, regex_pattern):
        self.tokenizer = Tokenizer(regex_pattern)
        self.current_token: (str, str) = ("empty", None)
        self.verbose = 1
        self.group_list = []
        self.rec_list = []
        self.nfa = NFA()

    def next_token(self):
        """
        Returns next token, saves it also in current_token variable
        """
        self.current_token = self.tokenizer.get_next_token()
        if self.verbose > 2:
            print("current token", self.current_token)

    def print_error(self, text):
        """
        Prints error message in case of reg-ex parse error
        """
        if self.verbose > 0:
            print("parse error at position: ", self.tokenizer.position, ", message: ", text, ", current token: ",
                  self.current_token)

    def print_log(self, text):
        if self.verbose > 1:
            print(text)

    def debug_decorator(func):
        """
        Decorator for parsing methods, used for debugging purposes.
        """
        verbose = 0

        def wrapper(*args, **kwargs):
            if verbose > 0:
                print(func.__name__ + " ((")

            ret = func(*args, **kwargs)

            if verbose > 0:
                print(")) " + func.__name__)

            return ret

        return wrapper

    def atom(self):
        """
        Atom is the basic syntactic element, it can be one of the following:
        *   string      -> string value to be exactly matched in the text
        *   hex, oct    -> a hexadecimal or octal code representation of a character
        *   back reference  -> a number referencing to a text matched by a match group
        *   multi match or negative multi match -> escaped char or a bracket[] group of chars representing multiple match
        *   a match group   -> an expression in round brackets ()

        'atom' = -->-+->--[characters]-->---------------------------------+
                    |                                                    |
                    +->--[.]---------->----------------------------------+
                    |                                                    |
                    +->-[(]-->--[expression]-->--[)]-->------------------+->-
                    |                                                    |
                    +->-[[]-->--[characterclass]-->--[]]-->--------------+
                    |                                                    |
                    +->-[[]-->--[~]-->--[characterclass]-->--[]]-->------+
        """
        if self.current_token[0] in ["string"]:
            state = State("str match", self.current_token[1], [self.current_token[1]], [])
            self.nfa.add_node(state)
            self.next_token()
            return True, state, [state]

        if self.current_token[0] in ["hex", "oct", "unicode"]:
            return self.parse_character_code_match()

        if self.current_token[0] in ["back reference"]:
            state = BackReferenceState(self.current_token[1], self.current_token[1], [])
            self.nfa.add_node(state)
            self.next_token()
            return True, state, [state]

        if self.current_token in [("meta", "^"), ("meta", "$"), ("escaped", "b"), ("escaped", "A"), ("escaped", "Z")]:
            state = BoundaryState("boundary " + self.current_token[1], self.current_token[1], [])
            self.nfa.add_node(state)
            self.next_token()
            return True, state, [state]

        if self.current_token[0] in ["escaped"]:
            # TODO: implement negative unicode multi match (with capitol P)
            # TODO: implement \X = match all characters including new line
            if self.current_token[1] in ["p", "P"]:
                return self.parse_unicode_multimatch(self.current_token[1] == "P")

            if self.current_token[1] in "swd":
                state = MultiMatchState("multi match", [], [])
                state.add_multi(self.current_token[1])
                self.nfa.add_node(state)
                self.next_token()
                return True, state, [state]
            else:
                state = State("esc match", "string_" + self.current_token[1], [self.current_token[1]], [])
                self.nfa.add_node(state)
                self.next_token()
                return True, state, [state]

        if self.current_token == ("meta", "."):
            self.next_token()
            state = MatchAllState(".", [])
            self.nfa.add_node(state)
            return True, state, [state]

        if self.current_token == ("meta", "("):
            return self.parse_match_group()

        if self.current_token == ("meta", "["):
            return self.parse_character_classes()

        if self.current_token in [("meta", "|"), ("meta", ")")]:
            return True

        self.print_error("Atom: end of atom reached, not interpretation for current token")
        return False, None, None

    def parse_match_group(self):
        """
        Handles match group - expression inside of round brackets
        """
        # register a match group
        self.nfa.max_match_group_no += 1
        max_match_group_no = self.nfa.max_match_group_no
        self.next_token()
        result, expression_state, expression_state_output = self.expression()
        if not result:
            return False, None, None
        if self.current_token == ("meta", ")"):
            # add match group
            # first check for a type of expression in ()
            # if it's repetition, we need to add a new state to handle the match group
            if expression_state.state_type == "repetition":
                match_state = ExpressionState("match group state", [expression_state])
                self.nfa.add_node(match_state)
                expression_state = match_state

            expression_state.match_group_start += [max_match_group_no]
            for state in expression_state_output:
                state.match_group_end += [max_match_group_no]

            self.next_token()
            return True, expression_state, expression_state_output
        else:
            self.print_error("Atom: expected \")\"")
            return False, None, None

    def parse_character_code_match(self):
        """
        Handles numerical codes of characters:
            * starting with x: \xFF are hexadecimal ASCII chars
            * starting with 0: \077 are octal ASCII chars
            * starting with u: \uFFFF are hexadecimal unicode code points
        """
        match_char = ""
        match_label = self.current_token[0]
        if match_label == "oct":
            dnum = int(self.current_token[1], 8)
            hnum = hex(dnum)
            match_char = str(bytes.fromhex(hnum[2:]).decode("ASCII"))
        elif match_label == "hex":
            print(self.current_token[1])
            match_char = str(bytes.fromhex(self.current_token[1]).decode("ASCII"))
        elif match_label == "unicode":
            match_char = chr(int(self.current_token[1], 16))
        match_label += " char match (" + self.current_token[1] + "->" + match_char + ")"
        state = State("char match", match_label, [match_char], [])
        self.nfa.add_node(state)
        self.next_token()
        return True, state, [state]

    def parse_unicode_multimatch(self, is_negative):
        """
        Handles unicode groups:
        * categories and subcategories
        * blocks
        * scripts
        """
        self.next_token()
        if self.current_token == ("meta", "{"):
            self.next_token()
            if self.current_token[0] != "string":
                self.print_error("Atom: expected unicode group, script or block name after {")
                return False, None, None
            unicode_group = self.current_token[1]

            self.next_token()
            if self.current_token != ("meta", "}"):
                self.print_error("Atom: expected } after {" + unicode_group)
                return False, None, None

            state = MultiMatchUnicodeState(unicode_group, unicode_group, [], is_negative)
            self.nfa.add_node(state)
            self.next_token()
            return True, state, [state]

        else:
            self.print_error("Atom: expected { after \\p")
            return False, None, None

    def parse_character_classes(self):
        """
        Handles character classes
        """
        self.next_token()

        negative_range = False
        if self.current_token == ("meta", "^"):
            negative_range = True
            self.next_token()

        if self.current_token[0] != "setelement" and self.current_token[0] != "escaped setelement" and \
                self.current_token[0] != "range setelement":
            self.print_error("Atom: expected set element")
            return False, None, None

        match: str = self.current_token[1]
        if negative_range:
            multi_match_state = NegativeMultiMatchState("neg multi match: " + match, [], [])
        else:
            multi_match_state = MultiMatchState("multi match: " + match, [], [])
        if self.current_token[0] == "range setelement":
            multi_match_state.add_range(match)
        elif self.current_token[0] == "escaped setelement":
            multi_match_state.add_multi(match)
        else:
            multi_match_state.match_values.append(match)
        self.nfa.add_node(multi_match_state)
        self.next_token()

        while self.current_token != ("meta", "]"):
            if self.current_token[0] != "setelement" and self.current_token[0] != "escaped setelement" and \
                    self.current_token[0] != "range setelement":
                self.print_error("Atom: expected set element")
                return False, None, None

            if self.current_token[0] == "range setelement":
                multi_match_state.add_range(self.current_token[1])
                multi_match_state.state_label += self.current_token[1]
            elif self.current_token[0] == "escaped setelement":
                multi_match_state.add_multi(self.current_token[1])
                multi_match_state.state_label += self.current_token[1]
            else:
                multi_match_state.match_values.append(self.current_token[1])
                multi_match_state.state_label += self.current_token[1]

            self.next_token()

        self.next_token()
        return True, multi_match_state, [multi_match_state]

    atom = debug_decorator(atom)

    def factor(self):
        """
        This method parses atom optionally followed by a character class.

        'factor' = -->-+->--[atom]-->-------------------+
                   |                                |
                   |                                |
                   +->--[atom]->-[metacharacters]->-+->--
        """
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

            recurring_state = RecurringState(rep_label + ": " + str(len(self.rec_list)) + " min=" + str(min_rep)
                                             + " max=" + str(max_rep), [atom_state], min_rep, max_rep)
            self.nfa.add_node(recurring_state)
            self.rec_list += [recurring_state]

            for out_state in output_states:
                out_state.loop_back_output_states.append(recurring_state)

            self.next_token()
            return True, recurring_state, [recurring_state]

        return True, atom_state, output_states

    factor = debug_decorator(factor)

    def term(self):
        """
        Parses one or more factors.

        'term' = -->-+->--[factor]-->----------+
                    |                         |
                    |                         |
                    +->--[factor]->-[term]-->-+->--
        """
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

    def expression(self):
        """
        Parses one or more terms delimited by |

        'expression' = -->-+->--[term]---->--------------------+
                          |                                   |
                          |                                   |
                          +->--[term]->-[|]->-[expression]-->-+->--
        """
        result, state, output_states = self.term()
        if not result:
            return False, None, None

        if self.current_token == ("end", None):
            end_state = EndState()
            self.nfa.add_node(end_state)
            for out_st in output_states:
                out_st.output_states.append(end_state)
            return True, state, output_states

        expression_state = None
        if self.current_token == ("meta", "|"):
            expression_state = ExpressionState("EXP", [state])
            self.nfa.add_node(expression_state)

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
            self.nfa.add_node(end_state)
            for out_st in output_states:
                out_st.output_states.append(end_state)
            output_states = None

        return True, state if expression_state is None else expression_state, output_states

    expression = debug_decorator(expression)

    def parse(self):
        """
        Parses reg-exp pattern
        """
        self.next_token()

        result, expression, output_state = self.expression()
        if not result:
            return False, None
        return self.current_token == ("end", None), expression

