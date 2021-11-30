class Tokenizer:
    """
    Tokenizer class is used to divide input pattern into tokens, that is chunks of text with a type.
    Type can be:
    * string        -> any text not containing meta characters, e.g. abc\xFA12\n3
    * meta          -> ().*+[]-\\^ also anchors, e.g. ^ $
    * end           -> end token
    * error         -> error token, contains error message
    * escaped       -> character preceded by \
    * setelement    -> e.g. a-z A-Z a x 1
    """

    def __init__(self, regex_pattern):
        self.regex_pattern = regex_pattern
        self.position = 0
        self.meta = "().*+?[]-\\^{}|,$"
        self.inside_char_set = False
        self.verbose = True
        self.current_token = None

    def get_next_token(self):
        """Main method, returns a single next token"""

        # Handling chars inside [], pt 1, covering ranges, e.g. A-Z and regular chars
        if self.inside_char_set \
                and self.regex_pattern[self.position] not in ["^", "\\", "]"]:  # TODO: check if valid logic
            if self.position + 1 >= len(self.regex_pattern):
                return "error", "unexpected end of pattern after: " + self.regex_pattern[self.position:]
            if self.regex_pattern[self.position + 1] == "-":
                if self.position + 2 >= len(self.regex_pattern):
                    return "error", "unexpected end of pattern after: " + self.regex_pattern[self.position:]
                self.position += 3
                return "range setelement", self.regex_pattern[self.position - 3: self.position]

            # if the char is not \, return one
            # escaped chars are handled after string loop
            self.position += 1
            return "setelement", self.regex_pattern[self.position - 1]

        # main string loop, lump all chars as long as they are regular
        # hex and octs are handles separately, that is, not lumped with regular chars
        char_string = ""
        while not self.inside_char_set \
                and self.position < len(self.regex_pattern) \
                and self.regex_pattern[self.position] not in self.meta:
            char_string += self.regex_pattern[self.position]
            self.position += 1

            # chars preceding recurrence meta, or anchors, like *, + or $ should be taken separately
            if self.position < len(self.regex_pattern) and self.regex_pattern[self.position] in "+*?{^$":
                # rollback
                if len(char_string) > 1:
                    self.position -= 1
                    return "string", char_string[:-1]
        if len(char_string) > 0:
            return "string", char_string

        # escaped characters and other meta characters
        if self.position < len(self.regex_pattern) and self.regex_pattern[self.position] in self.meta:
            meta_char = self.regex_pattern[self.position]

            if meta_char == "\\":  # resolve escaped characters
                if self.position + 1 == len(self.regex_pattern):
                    return "error", "unexpected end of pattern after: \\"
                self.position += 1
                escaped_char = self.regex_pattern[self.position]

                if escaped_char in "ptnrfvsSwWdDbAZ" or escaped_char in self.meta:
                    self.position += 1
                    return "escaped" if not self.inside_char_set else "escaped setelement", escaped_char

                # handling back references
                if escaped_char in "123456789":
                    self.position += 1
                    if self.position < len(self.regex_pattern) and self.regex_pattern[self.position] in "0123456789":
                        self.position += 1
                        return "back reference", escaped_char + self.regex_pattern[self.position-2:self.position]
                    return "back reference", escaped_char

                if escaped_char == "x":  # get hex (next two chars)
                    if self.position + 2 >= len(self.regex_pattern):
                        return "error", "unexpected end of pattern after: \\x"
                    hex_char = self.regex_pattern[self.position + 1: self.position + 3]
                    if hex_char[0] not in "0123456789ABCDEF" or hex_char[1] not in "0123456789ABCDEF":
                        return "error", "incorrect hex: " + hex_char
                    self.position += 3
                    return "hex", hex_char

                if escaped_char == "u":  # get unicode (next four chars)
                    if self.position + 4 >= len(self.regex_pattern):
                        return "error", "unexpected end of pattern after: \\x"
                    unicode_char = self.regex_pattern[self.position + 1: self.position + 5]
                    if unicode_char[0] not in "0123456789ABCDEF" or unicode_char[1] not in "0123456789ABCDEF" or \
                            unicode_char[2] not in "0123456789ABCDEF" or unicode_char[3] not in "0123456789ABCDEF":
                        return "error", "incorrect unicode: " + unicode_char
                    self.position += 5
                    return "unicode", unicode_char

                if escaped_char == "0":  # get oct (next two chars)
                    if self.position + 2 >= len(self.regex_pattern):
                        return "error", "unexpected end of pattern after: \\0"
                    oct_char = self.regex_pattern[self.position + 1: self.position + 3]
                    if oct_char[0] not in "01234567" or oct_char[1] not in "01234567":
                        return "error", "incorrect oct: " + oct_char
                    self.position += 3
                    return "oct", oct_char

                return "error", "unsupported escaped character: " + escaped_char

            if meta_char == "[":
                self.inside_char_set = True
            elif meta_char == "]":
                self.inside_char_set = False

            self.position += 1

            return "meta", meta_char
        elif self.position == len(self.regex_pattern):
            return "end", None
        else:
            return "error", self.regex_pattern[self.position]

    def next_token(self):
        """Assigns a token to current token variable"""
        self.current_token = self.get_next_token()
        if self.verbose:
            print("current token", self.current_token)
