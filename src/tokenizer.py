class Tokenizer:
    def __init__(self, regExText_):
        self.regExText = regExText_
        self.position = 0
        self.meta = "().*+[]-\^{}|"
        self.insideCharSet = False
        self.verbose = True
        
        
    # type is: 
    # - string -> any text not containing meta characters, e.g. abc\xFA12\n3
    # - meta -> ().*+[]-\^
    # - end
    # - error
    # - escaped
    # - setelement -> e.g. a-z A-Z a x 1 
    def get_next_token(self):
        # handling chars inside [], pt 1, covrring ranges, e.g. A-Z and regular chars
        if self.insideCharSet and self.regExText[self.position] not in ["\\", "]"]: #inside [] all chars should be took separatelly
            if self.position + 1 >= len(self.regExText):
                return ("error", "unexpected end of file after: " + self.regExText[self.position:])
            if self.regExText[self.position + 1] == "-":
                if self.position + 2 >= len(self.regExText):
                    return ("error", "unexpected end of file after: " + self.regExText[self.position:])
                self.position += 3
                return ("range setelement", self.regExText[self.position - 3: self.position])
            
            # if the char is not \, return one
            # escaped chars are handled after string loop
            self.position += 1
            return ("setelement", self.regExText[self.position - 1])
                
        # main string loop, lump all chars as long as they are regular
        # hex and octs are handles separatelly, that is, not lumped with regular chars
        char_string = ""
        while not self.insideCharSet and self.position < len(self.regExText) and self.regExText[self.position] not in self.meta:
            char_string += self.regExText[self.position]
            self.position += 1
            
            #chars preceeding recurrence meta, like * or + should be taken separatelly
            if self.position < len(self.regExText) and self.regExText[self.position] in "+*?":
                #rollback 
                if len(char_string) > 1:
                    self.position -= 1
                    return ("string", char_string[:-1])    
        if len(char_string) > 0:
            return ("string", char_string)

        # escaped characters and other meta characters
        if self.position < len(self.regExText) and self.regExText[self.position]  in self.meta:
            meta_char = self.regExText[self.position]
            
            if meta_char == "\\": # resolve escaped characters
                if self.position + 1 == len(self.regExText):
                    return ("error", "unexpected end of file after: \\")
                self.position += 1
                escaped_char = self.regExText[self.position]
                
                if escaped_char in "tnrfvsSwWdD" or escaped_char in self.meta:
                    self.position += 1
                    return ("escaped" if not self.insideCharSet else "escaped setelement", escaped_char)
                
                if escaped_char == "x": # get hex (next two chars)
                    if self.position + 2 >= len(self.regExText):
                        return ("error", "unexpected end of file after: \\x")
                    hex = self.regExText[self.position + 1: self.position + 3]
                    if hex[0] not in "0123456789ABCDEF" or hex[1] not in "0123456789ABCDEF":
                        return ("error", "incorrect hex: " + hex)
                    self.position += 3
                    return("hex", hex)

                if escaped_char == "0": # get oct (next two chars)
                    if self.position + 2 >= len(self.regExText):
                        return ("error", "unexpected end of file after: \\0")
                    oct = self.regExText[self.position + 1: self.position + 3]
                    if oct[0] not in "01234567" or oct[1] not in "01234567":
                        return ("error", "incorrect oct: " + oct)
                    self.position += 3
                    return("oct", oct)
                
                return ("error", "unsupported escaped character: " + escaped_char)
           
            if meta_char == "[":
                self.insideCharSet = True
            elif meta_char == "]":
                self.insideCharSet = False
        
            self.position += 1
            return ("meta", meta_char)
        elif self.position == len(self.regExText):
            return ("end", None)
        else:
            return ("error", self.regExText[self.position])
        
    def next_token(self):
        self.current_token = self.get_next_token()
        if self.verbose:
            print("current token", self.current_token)
