from regex_parser import RegExParser
from interpreter import Interpreter


if __name__ == '__main__':
    # regex = RegExParser("(19|20)\\d\\d[- /.](0[1-9]|1[012])[- /.](0[1-9]|[12][0-9]|3[01])\\.人+")
    # regex = RegExParser("((\\w{2} ){3,4})(19|20)\\d\\d")
    # regex = RegExParser("<([A-Z]+)>(19|20)\\d\\d[- /.](0[1-9]|1[012])[- /.](0[1-9]|[12][0-9]|3[01])</\\0>")
    regex = RegExParser("(.*|.*)*")

    result, nfa = regex.parse()

    if result:
        for node in regex.nsa.node_list:
            print(node.to_string())
            print(node.output_states_to_string())

        interpreter = Interpreter(nfa, "<HTML>My birthday</HTML> is on <DATE>1977-09-14</DATE>.人人生MyMy")
        interpreter.verbose = 1
        match_list = interpreter.run()

        for match in match_list:
            print(match.to_string())

