from tokenizer import Tokenizer

class RegExParser:
    def __init__(self, regExText_):
        self.tokenizer = Tokenizer(regExText_)
        self.current_token = ("empty", None)
        self.verbose = 0

    def next_token(self):
        self.current_token = self.tokenizer.get_next_token()
        if self.verbose > 2:
            print("current token", self.current_token)
        
    def print_error(self, text):
        if self.verbose > 0:
            print("parse error at position: ", self.position, ", message: ", text, ", current token: ", self.current_token)
    
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
        if self.current_token[0] in ["string", "escaped", "hex", "oct"]:
            state = State("string match", "match string: " + self.current_token[1], [self.current_token[1]], [])
            self.next_token()
            return True, state, [state]
        
        if self.current_token[0] == "meta" and self.current_token[1] == ".":
            self.next_token()
            state = MatchAllState( ".", [])
            return True, state, [state]

        if self.current_token[0] == "meta" and self.current_token[1] == "(":
            self.next_token()
            
            result, expression_state, expression_state_output = self.expression()
            if not result:
                return False, None, None
            
            if self.current_token[0] == "meta" and self.current_token[1] in ")":
                self.next_token()
                return True, expression_state, expression_state_output
            else:
                self.print_error("Atom: expected \")\"")
                return False, None, None
  
        if self.current_token[0] == "meta" and self.current_token[1] == "[":
            self.next_token()
                        
            if self.current_token[0] != "setelement" and self.current_token[0] != "escaped setelement" and self.current_token[0] != "range setelement":
                self.print_error("Atom: expected set element")
                return False, None, None
            
            match = self.current_token[1]
            multiMatchState = MultiMatchState("multi match: " + match, [], [])
            if self.current_token[0] == "range setelement":
                multiMatchState.add_range(match)
            elif self.current_token[0] == "escaped setelement":
                multiMatchState.add_multi(match)
            else:
                multiMatchState.match_values.append(match)
            
            self.next_token()        
            
            while self.current_token != ("meta", "]"):
                if self.current_token[0] != "setelement" and self.current_token[0] != "escaped setelement" and self.current_token[0] != "range setelement":
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
    
        
    #'factor' = -->-+->--[atom]-->-------------------+
    #               |                                |
    #               |                                |
    #               +->--[atom]->-[metacharacters]->-+->--
    def factor(self):
        ouput_states = []
        result, atom_state, ouput_states = self.atom()
        if not result:
            return False, None, None
        
        if self.current_token == ("end", None):
            return True, atom_state, ouput_states
        
        # TODO: handle {}
        if self.current_token in [("meta", "+"), ("meta", "*"), ("meta", "?")]:
            
            min_rep, max_rep = 1, 1
            
            if self.current_token == ("meta", "+"):
                min_rep, max_rep = 1, -1
            if self.current_token == ("meta", "*"):
                min_rep, max_rep = 0, -1            
            if self.current_token == ("meta", "?"):
                min_rep, max_rep = 0, 1
                
            recurring_state = RecurringState(self.current_token[1], [atom_state], min_rep, max_rep)
            for out_state in ouput_states:
                out_state.output_states.append(recurring_state)

            self.next_token()
            return True, atom_state, [recurring_state]
        
        return True, atom_state, ouput_states
    
    factor = debug_decorator(factor) 
    
    #'term' = -->-+->--[factor]-->----------+
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

        

    #'expression' = -->-+->--[term]---->--------------------+
    #                   |                                   |
    #                   |                                   |
    #                   +->--[term]->-[|]->-[expression]-->-+->--
    def expression(self):
        result, state, output_states = self.term() 
        if not result:
            return False, None, None

        if self.current_token == ("end", None):
            end_state = EndState()
            for out_st in output_states:
                out_st.output_states.append(end_state)
            return True, state, output_states

        expression_state = None
        if self.current_token == ("meta", "|"):
            expression_state = ExpressionState("EXP", [state])
            
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
            for out_st in output_states:
                out_st.output_states.append(end_state)
            output_states = None
        
        return True, state if expression_state is None else expression_state, output_states
        
    expression = debug_decorator(expression)
        
    def parse(self):
        self.next_token()
        
        result, expression, output_state = self.expression()
        if not result:
            return False
        return self.current_token == ("end", None), expression
        
