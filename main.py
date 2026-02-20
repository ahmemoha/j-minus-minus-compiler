import sys
sys.path.insert(0, '/home/profs/aycock/411/lib/antlr4/python3.13') # ensure the cpsc411 library path is loaded
import os
from antlr4 import *
from antlr4.error.ErrorListener import ErrorListener
from Jminus import Jminus
from JminusParser import JminusParser
from cpsc411.astshaper import ASTShaper

# AST shape specification for J--
# we'll build this incrementally based on ASTShaper warnings
SHAPE_SPEC = """
"""

# updated error listener for Milestone 2
# made a error listener to handle crashes or errors properly
class FatalErrorListener(ErrorListener):
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        # Milestone 2 spec: Error and warning messages should go to standard error. You should exit immediately after an error message.
        sys.stderr.write(f"error: syntax error at or near line {line}\n") 
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
    input_stream = FileStream(input_path, encoding='utf-8', errors='replace')

    # have out lexer initialized
    lexer = Jminus(input_stream)

    # add error listener
    lexer.removeErrorListeners()
    lexer.addErrorListener(FatalErrorListener())


    # Milestone 2 parser code
    # create a token stream from the lexer
    token_stream = CommonTokenStream(lexer)

    # initialize the Parser
    parser = JminusParser(token_stream)

    # attach your FatalErrorListener to the Parser too
    parser.removeErrorListeners()
    parser.addErrorListener(FatalErrorListener())

    # parse the input starting at the 'start' rule
    tree = parser.start()

    # build the AST using ASTShaper
    shaper = ASTShaper(SHAPE_SPEC)
    ast = shaper.shapetree(tree)

    # print the textual representation of the AST
    print(ast)

if __name__ == '__main__':
    main()

