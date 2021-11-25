class Tokenizer:
    """
    Tokenizer class is used to devide input pattern into tokens, that is chunks of text with a type.
    Type can be:
    * string -> any text not containing meta characters, e.g. abc\xFA12\n3
    * meta -> ().*+[]-\^ also anchors, e.g. ^ $
    * end -> end token
    * error -> error token, contains error message
    * escaped
    * setelement -> e.g. a-z A-Z a x 1
    """

    def __init__(self, regex_pattern):
        self.regExText = regex_pattern
        self.position = 0
        self.meta = "().*+?[]-\\^{}|,$"
        self.insideCharSet = False
        self.verbose = True
        self.current_token = None

    def get_next_token(self):
        """Main method, returns a single next token"""

        # Handling chars inside [], pt 1, covering ranges, e.g. A-Z and regular chars
        if self.insideCharSet and self.regExText[self.position] not in ["^", "\\",
                                                                        "]"]:  # inside [] all chars should be took separatelly
            if self.position + 1 >= len(self.regExText):
                return "error", "unexpected end of file after: " + self.regExText[self.position:]
            if self.regExText[self.position + 1] == "-":
                if self.position + 2 >= len(self.regExText):
                    return "error", "unexpected end of file after: " + self.regExText[self.position:]
                self.position += 3
                return "range setelement", self.regExText[self.position - 3: self.position]

            # if the char is not \, return one
            # escaped chars are handled after string loop
            self.position += 1
            return "setelement", self.regExText[self.position - 1]

        # main string loop, lump all chars as long as they are regular
        # hex and octs are handles separately, that is, not lumped with regular chars
        char_string = ""
        while not self.insideCharSet \
                and self.position < len(self.regExText) \
                and self.regExText[self.position] not in self.meta:
            char_string += self.regExText[self.position]
            self.position += 1

            # chars preceding recurrence meta, or anchors, like *, + or $ should be taken separately
            if self.position < len(self.regExText) and self.regExText[self.position] in "+*?{^$":
                # rollback
                if len(char_string) > 1:
                    self.position -= 1
                    return "string", char_string[:-1]
        if len(char_string) > 0:
            return "string", char_string

        # escaped characters and other meta characters
        if self.position < len(self.regExText) and self.regExText[self.position] in self.meta:
            meta_char = self.regExText[self.position]

            if meta_char == "\\":  # resolve escaped characters
                if self.position + 1 == len(self.regExText):
                    return "error", "unexpected end of file after: \\"
                self.position += 1
                escaped_char = self.regExText[self.position]

                if escaped_char in "tnrfvsSwWdDbAZ" or escaped_char in self.meta:
                    self.position += 1
                    return "escaped" if not self.insideCharSet else "escaped setelement", escaped_char

                # handling back references
                if escaped_char in "0123456789":
                    self.position += 1
                    if self.position < len(self.regExText) and self.regExText[self.position] in "0123456789":
                        self.position += 1
                        return "back reference", escaped_char+self.regExText[self.position]
                    return "back reference", escaped_char

                if escaped_char == "x":  # get hex (next two chars)
                    if self.position + 2 >= len(self.regExText):
                        return "error", "unexpected end of file after: \\x"
                    hex = self.regExText[self.position + 1: self.position + 3]
                    if hex[0] not in "0123456789ABCDEF" or hex[1] not in "0123456789ABCDEF":
                        return "error", "incorrect hex: " + hex
                    self.position += 3
                    return "hex", hex

                if escaped_char == "0":  # get oct (next two chars)
                    if self.position + 2 >= len(self.regExText):
                        return "error", "unexpected end of file after: \\0"
                    oct = self.regExText[self.position + 1: self.position + 3]
                    if oct[0] not in "01234567" or oct[1] not in "01234567":
                        return "error", "incorrect oct: " + oct
                    self.position += 3
                    return "oct", oct

                return "error", "unsupported escaped character: " + escaped_char

            if meta_char == "[":
                self.insideCharSet = True
            elif meta_char == "]":
                self.insideCharSet = False

            self.position += 1

            return "meta", meta_char
        elif self.position == len(self.regExText):
            return "end", None
        else:
            return "error", self.regExText[self.position]

    def next_token(self):
        """Assigns a token to current token variable"""
        self.current_token = self.get_next_token()
        if self.verbose:
            print("current token", self.current_token)
