import sys
import os
from antlr4 import *
from antlr4.error.ErrorListener import ErrorListener
from Jminus import Jminus


# made a error listener to handle crashes or errors properly
class FatalErrorListener(ErrorListener):
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        sys.stderr.write(f"warning: unknown char at or near line {line}\n") # Matches the reference output format exactly
        sys.exit(1)

def main():
    # check for the arguments
    if len(sys.argv) != 2:
        sys.stderr.write("Usage: python3 main.py <input_file>\n")
        sys.exit(1)

    input_path = sys.argv[1]

    # see if the file exists
    if not os.path.isfile(input_path):
        sys.stderr.write(f"Error: File '{input_path}' not found.\n")
        sys.exit(1)

    # set t up the stream
    input_stream = FileStream(input_path, encoding='utf-8')

    # have out lexer initialized
    lexer = Jminus(input_stream)

    # add error listener
    lexer.removeErrorListeners()
    lexer.addErrorListener(FatalErrorListener())

    # now have it process tokens
    token = lexer.nextToken()
    while token.type != Token.EOF:
        # get the symbolic name from the grammar or fallback to ID
        rule_name = lexer.symbolicNames[token.type]
        if not rule_name:
            rule_name = str(token.type)

        # print to stdout
        print(f"{rule_name} @ line {token.line}, attr '{token.text}'")
        token = lexer.nextToken()

if __name__ == '__main__':
    main()
