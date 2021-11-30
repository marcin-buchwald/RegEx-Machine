class Step:
    """Each matching state generates a step, this class represent it"""
    def __init__(self, state, position, match_len, text, prev_step, step_no):
        self.state = state
        self.position = position  # position in text, the beginning of the string to be matched
        self.match_len = match_len
        self.text = text
        self.prev_step: Step = prev_step
        self.rep_counter = 1  # for recurrent steps
        self.step_no = step_no
        self.back_ref_text = None

    def matched_text(self):
        """Returns the text matched at the step"""
        return self.text[self.position:self.position + self.match_len]

    def to_string(self):
        """Returns a string containing important information about the step"""
        matched_text = self.matched_text()
        if len(matched_text) > 0:
            matched_text = " : " + matched_text

        if self.state.state_type == "recurrence":
            return "(" + self.state.state_label + ")" + str(self.rep_counter)

        return "(" + self.state.state_label + ")" + matched_text


class MatchResult:
    """The result of match method, contains position in text, matched text and list of all steps leading to the match"""
    def __init__(self, position, matched_text, step_list):
        self.position = position
        self.matched_text = matched_text
        self.step_list = step_list

    @classmethod
    def from_steps(cls, last_step):
        """Initialize w MatchResult object from a list of steps found by match method"""
        s = last_step

        out_string = s.matched_text()
        out_steps = [s]

        while s.prev_step is not None:
            s = s.prev_step
            out_string = s.matched_text() + out_string
            out_steps = [s] + out_steps

        ret = cls(s.position, out_string, out_steps)

        return ret

    def to_string(self):
        """Returns a string containing important information about the match result"""
        return self.matched_text + " (pos: " + str(self.position) + ")"


class Interpreter:
    """Interpreter class performs matching, has 2 main methods:
    * match(position), tries to match a pattern at a position
    * run(), performs match at every position of the input text
    """
    def __init__(self, nfa):
        self.nfa = nfa
        # self.text = text
        self.next_turn = []
        self.current_turn = []
        self.matches = []  # list of tuples (start_pos, end_pos)
        self.verbose = 0

    def match_all(self, text):
        """Loop over the text and call Interperter.match() for every character of the text"""
        match_list = []
        max_reached_position = 0
        while max_reached_position < len(text):
            ret = self.match(text, max_reached_position)
            if ret is not None:
                max_reached_position = ret.position + len(ret.matched_text)
                match_list += [ret]
            else:
                max_reached_position += 1

        return match_list

    def match_first(self, text):
        """Return the first match of the pattern in the text"""
        return self.match(text, 0)


    @staticmethod
    def get_rep_counter(last_step, rec_state_label):
        """Return number of recurrences of the same label (ID) in the step list leading up to last_step
        inclusive the last step"""

        s = last_step

        if s is not None and s.state.state_label == rec_state_label:
            return s.rep_counter

        while s.prev_step is not None:
            s = s.prev_step

            if s is not None and s.state.state_label == rec_state_label:
                return s.rep_counter

        return 1

    @staticmethod
    def can_go_recurrent(current_step, new_state_label):
        """Check if there's a cycle in the NFA, by looking into cyclical references of recurrent nodes without
        any matching characters between them"""

        s = current_step

        while s.prev_step is not None:
            s = s.prev_step

            if s.state.state_type not in ["recurrence", "expression"]:
                return True

            if s.state.state_label == new_state_label:
                return False

        return True

    def match(self, text, position):
        """Return matching string starting at the position
        Algorithm: start with node START, create a list current_state_list = [START], this list will contain steps
        to be processed current turn
        Iterate over output_states of each node from current_state_list:
        - put every state that returned is_matched = True on the next_state_list step list
        - once current_state_list is empty, swap current end next lists
        - if current step is END -> record match, always keep the longest match
        - if text is over or both current and next lists are empty, end loop
        """

        max_position_reached = position
        max_match_step = None

        matched, match_len = self.nfa.is_matched(text, position)

        # check if the first node matched, if not, no match at all
        if not matched:
            if self.verbose > 1:
                print("No match at position ", position)
            return None

        step = Step(self.nfa, position, match_len, text, None, 0)
        self.define_match_groups(step)
        current_state_list = [step]
        next_state_list = []

        # step_count = 1

        while len(current_state_list) > 0 or len(next_state_list) > 0:
            if len(current_state_list) == 0:
                # step_count = len(next_state_list)
                # print("step cnt: ", step_count)
                # print("pos: ", current_step.position)

                current_state_list = next_state_list
                next_state_list = []

            current_step = current_state_list.pop(0)

            if self.verbose > 1:
                print("State: ", current_step.state.state_type, " ", current_step.state.state_label)
                print("Match: ", text[current_step.position:current_step.position + current_step.match_len])

            # match found, record it and move on
            if current_step.state.state_type == "end":
                # to avoid duplicates in the match_list, check if the match is already there
                # if current_step.position not in match_list:
                if max_position_reached < current_step.position:
                    max_position_reached = current_step.position
                    max_match_step = current_step
                continue

            # prepare list of current state's output states, to append it (if they match) to the next step list
            output_state_list = current_step.state.output_states + current_step.state.loop_back_output_states
            if current_step.state.state_type == "repetition":
                rep_counter = self.get_rep_counter(current_step, current_step.state.state_label)

                # if the min loop counter wasn't reached, allow only looping back for next repetition
                if rep_counter < current_step.state.min_rep + 1:
                    output_state_list = current_step.state.loop_output_states
                # if max loop counter wasn't reached, allow looping back for next repetition along with going forward
                elif rep_counter <= current_step.state.max_rep + 1:
                    output_state_list += current_step.state.loop_output_states

            for output_state in output_state_list:
                # check if the step is already on the list
                if not self.add_to_list(current_step, output_state, next_state_list):
                    continue

                # check for recurrence cycles without char matching
                if current_step.state.state_type == "repetition" and output_state.state_type == "repetition":
                    if not self.can_go_recurrent(current_step, output_state.state_label):
                        continue

                # check if output state matches text at a position, first check if the state is a back reference
                if output_state.state_type == "back reference":
                    reference = self.get_back_ref_text(int(output_state.ref_no), current_step)
                    matched, new_match_len = output_state.is_matched(text,
                                                                     current_step.position + current_step.match_len,
                                                                     reference)
                # check for the types of state
                else:
                    matched, new_match_len = output_state.is_matched(text,
                                                                     current_step.position + current_step.match_len)
                if matched:
                    step = Step(
                        output_state,
                        current_step.position + current_step.match_len,
                        new_match_len,
                        text,
                        current_step,
                        current_step.step_no + 1
                    )

                    # update repetition counter if came here via loop_back_output_state (i.e. from within the loop)
                    if output_state.state_type == "repetition":
                        if output_state not in current_step.state.loop_back_output_states:
                            # reset output_state's counter
                            step.rep_counter = 1
                        else:
                            rep_counter = self.get_rep_counter(current_step, output_state.state_label)
                            if rep_counter > output_state.max_rep:
                                continue
                            step.rep_counter = rep_counter + 1

                    next_state_list.append(step)
                    self.define_match_groups(step)
        if max_match_step is None:
            return None
        return MatchResult.from_steps(max_match_step)
        # return list(match_list.values())

    def define_match_groups(self, step):
        """Record text matched by a match group in a step"""
        # match groups
        if step.state.match_group_end is not []:  # add all match end states to nfa.match_groups
            for match_group in step.state.match_group_end:
                match_text = self.find_match_text(match_group, step)

                if len(match_text) > 0:
                    # print("match text for group: ", match_group, " = ", match_text)
                    # if match text is not empty, save it in the current step
                    step.back_ref_text = match_text

    @staticmethod
    def add_to_list(current_step, output_state, next_state_list):
        """
        Helper function to avoid adding steps that contain states already on the list and with positions
        greater or equal to checked step
        """
        for sss in next_state_list:
            if output_state == sss.state and current_step.position + current_step.match_len >= sss.position:
                return False
        return True

    @staticmethod
    def find_match_text(match_group_name, match_end_step):
        """Helper function to find match group text"""
        match_text = match_end_step.matched_text()
        step = match_end_step.prev_step
        while step is not None:

            match_text = step.matched_text() + match_text
            if match_group_name in step.state.match_group_start:
                return match_text
            step = step.prev_step
        return match_text

    @staticmethod
    def get_back_ref_text(ref_no, current_step):
        """Helper function to find text of a match group references by ref_no"""
        step = current_step
        while step is not None:
            if ref_no in step.state.match_group_end:
                return step.back_ref_text
            step = step.prev_step
        return None
