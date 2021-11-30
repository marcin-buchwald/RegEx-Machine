from regex_parser import RegExParser
from interpreter import Interpreter


class RegEx:
    """Facade of the RegEx Machine"""

    verbose = 0

    def __init__(self, pattern):
        self.regex_parser = RegExParser(pattern)
        result, nfa = self.regex_parser.parse()
        if result:
            self.interpreter = Interpreter(nfa)
        else:
            self.interpreter = None

    def match_all(self, text):
        return self.interpreter.match_all(text)

    def match_first(self, text):
        return self.interpreter.match_first(text)

    def print_graph(self):
        print(self.regex_parser.tokenizer.regex_pattern)
        self.regex_parser.nfa.print_graph()


