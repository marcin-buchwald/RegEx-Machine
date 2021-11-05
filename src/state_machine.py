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
        
    def is_matched(self, text, position):
        if self.state_type == "string match":
            if position+len(self.match_values[0]) > len(text):
                return False, 0
            
            match = text[position:position+len(self.match_values[0])] == self.match_values[0]
            return match, len(self.match_values[0]) if match else 0

                              

class EndState(State):
    def __init__(self):
        super().__init__("end", "end", None, None)
     
    def is_matched(self, text, position):
        return True, 0

        
class MultiMatchState(State):
    def __init__(self, state_label, match_values, output_states):
        super().__init__("multi match", state_label, match_values, output_states)
        
    #range is: [a-z]
    def add_range(self, range_str):
        if len(range_str) < 3 or range_str[1] != "-":
            return False
        
        self.match_values += [chr(x) for x in range(ord(range_str[0]), ord(range_str[2]) + 1)]
        return True
    
    #digit, word (digit, letter, underscore), white space is: \d \w \s
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
    

class NegativeMultiMatchState(State):
    def __init__(self, state_label, output_states):
        super().__init__("negative multi match", state_label, match_values, output_states)
     
    def is_matched(self, text, position):
        if position >= len(text):
            return False
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
    def __init__(self, state_label, output_states, min_rep, max_rep):
        self.min_rep = min_rep
        self.max_rep = max_rep
        
        super().__init__("recurrence", state_label, None, output_states)
     
    def is_matched(self, text, position):
        # recurrence and choice are states without match values, they simply let the interpreter enter them
        # than the interpreter iterates over output states to check if any of them match
        return True, 0


class ExpressionState(State):
    def __init__(self, state_label, output_states):
        super().__init__("expression", state_label, None, output_states)
     
    def is_matched(self, text, position):
        # recurrence and choice are states without match values, they simply let the interpreter enter them
        # than the interpreter iterates over output states to check if any of them match
        return True, 0
 
    
class Step:
    def __init__(self, state, position, match_len, text, prev_step):
        self.state = state
        self.position = position #position in text, the beginning of the string to be matched
        self.match_len = match_len
        self.text = text
        self.prev_step = prev_step
        
    def matched_text(self):
        return self.text[self.position:self.position+self.match_len]

    def to_string(self):
        return self.matched_text()

class Interpreter:
    def __init__(self, nfa, text):
        self.nfa = nfa
        self.text = text
        self.next_turn = []
        self.current_turn = []
        self.matches = []  # list of tuples (start_pos, end_pos)
        self.verbose = 0
    
    # start with node START, init local var position = 0, create a list next_turn = [], this list will contain staps to be processed next turn
    # iterate over output_states of START node -> call is_matched(text, 0)
    # put every state that returned is_matched = True on the next_turn step list, the step.position is 0
    # create a loop while next_turn is not empty:
    # current_turn = next_turn
    # next_turn = []
    # iterate over current_turn:
    # for every step in current_turn
    #   if current step is END -> Return 'MATCH'
    #   if text is over -> Return 'NOT MATCH'
    #   step.position += length of match of the state 
    #   iterate over output_states of the step
    #       put every matching state on the next_turn list, with current step's position
    
    # open topics:
    # - how to handle text that don't match whole the pattern
    #   that is to find a substring of the text that wholy matches the pattern
    # - how to record parts of the text that match the pattern
    
    # loop over the text and call Interperter.match() for every character of the text
    def run(self):
        for pos in range(len(self.text)):
            self.multi_match_upgrade(pos)
 

    def multi_match(self, position):
        match_list = []
        
        
        matched, match_len = self.nfa.is_matched(self.text, position)
        # check if the first node matched, if not, no match at all
        if not matched:
            if self.verbose > 0:
                print("No match")
            return False

        current_state_list = [(self.nfa, position, match_len, self.text[position:position+match_len])]
        next_state_list = []    
                
        while len(current_state_list) > 0 or len(next_state_list) > 0:
            if len(current_state_list) == 0:
                current_state_list = next_state_list
                next_state_list = []
            
            current_state, current_position, match_len, currently_matched = current_state_list.pop(0)
            
            if self.verbose > 1:
                print("State: ", current_state.state_type, " ", current_state.state_label)
                print("Match: ", self.text[current_position:current_position + match_len])            
            
            # return first matched
            # TODO: record the match and continue until a number of matches is found, or number of iteration is exceeded
            if current_state.state_type == "end":
                if self.verbose > 0:
                    print("MATCH!!!! " + currently_matched)
                match_list.append(currently_matched)
                #return True
            
            if current_state.output_states is None:
                continue
    
            for output_state in current_state.output_states:
                matched, new_match_len = output_state.is_matched(self.text, current_position + match_len)
                if matched:
                    next_state_list.append((output_state, 
                                            current_position + match_len, 
                                            new_match_len, 
                                            currently_matched+":"+self.text[current_position + match_len:current_position + match_len+new_match_len]))
        
        if self.verbose > 0:
            print("No match")
        return False   


    def multi_match_upgrade(self, position):
        match_list = []
        
        
        matched, match_len = self.nfa.is_matched(self.text, position)
        # check if the first node matched, if not, no match at all
        if not matched:
            if self.verbose > 1:
                print("No match")
            return False

        current_state_list = [Step(self.nfa, position, match_len, self.text, None)]#[position:position+match_len]
        next_state_list = []    
                
        while len(current_state_list) > 0 or len(next_state_list) > 0:
            if len(current_state_list) == 0:
                current_state_list = next_state_list
                next_state_list = []
            
            current_step = current_state_list.pop(0)
            # current_state, current_position, match_len, currently_matched 
            
            if self.verbose > 1:
                print("State: ", current_step.state.state_type, " ", current_step.state.state_label)
                print("Match: ", self.text[current_step.position:current_step.position + current_step.match_len])            
            
            # return first matched
            # TODO: record the match and continue until a number of matches is found, or number of iteration is exceeded
            if current_step.state.state_type == "end":
                s = current_step
                out_string = [s.to_string()]
                while s.prev_step is not None:
                    s = s.prev_step
                    out_string = [s.to_string()] + out_string
                match_list.append(out_string)

                if self.verbose > 0:
                    print("MATCH!!!! ")                    
                    print("".join(out_string))
            
            if current_step.state.output_states is None:
                continue
    
            for output_state in current_step.state.output_states:
                matched, new_match_len = output_state.is_matched(self.text, current_step.position + current_step.match_len)
                if matched:
                    next_state_list.append(
                        Step(
                            output_state, 
                            current_step.position + current_step.match_len, 
                            new_match_len, 
                            self.text,
                            current_step
                        )
                    )
        
        if self.verbose > 1:
            print("No match")
        return False   

