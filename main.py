import sys
sys.path.insert(0, '/home/profs/aycock/411/lib/antlr4/python3.13') # ensure the cpsc411 library path is loaded
import os
from antlr4 import *
from antlr4.error.ErrorListener import ErrorListener
from Jminus import Jminus
from JminusParser import JminusParser
from cpsc411.astshaper import ASTShaper
from cpsc411.ast import AST
from semantic import check_semantics
import re

# updated error listener for Milestone 2
# made a error listener to handle crashes or errors properly
class FatalErrorListener(ErrorListener):
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        # Milestone 2 spec: Error and warning messages should go to standard error. You should exit immediately after an error message.
        sys.stderr.write(f"error: {msg} at or near line {line}\n")
        sys.exit(1)

# custom string class just above main()
class SymString(str):
    """ this tricks Python into printing sym7 instead of 'sym7'"""
    def __repr__(self):
        return self

# inside main, right before you print the AST, iterate through it to wrap sym strings
def fix_sym_quotes(node):
    if not hasattr(node, 'type'):
        return
    if hasattr(node, 'sym') and isinstance(node.sym, str):
        # wrap the sym_id in our custom string class so it prints without quotes
        node.sym = SymString(node.sym)
    for child in getattr(node, 'children', []):
        fix_sym_quotes(child)


def fold_uminus(node):
    # if it's not an AST node like a raw token, just return it
    if not hasattr(node, 'type'):
        return node

    # if this is a UMINUS node, and its only child is a 'number', fold it
    if node.type == 'UMINUS' and len(node) == 1 and getattr(node[0], 'type', '') == 'number':
        # grab the line number from the UMINUS node
        lineno = getattr(node, 'lineno', getattr(node[0], 'lineno', 0))
        # create and return a brand new folded number node
        return AST('number', attr='-' + node[0].attr, lineno=lineno)

    # otherwise safely reconstruct the current node
    # we grab its attributes like lineno, attr but ignore internal lists
    attrs = {k: v for k, v in vars(node).items() if k not in ('type', 'children') and not isinstance(v, list)}
    new_node = AST(node.type, **attrs)

    # recursively fold all the children
    for child in node:
        new_node.append(fold_uminus(child))

    return new_node



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

    # Read the shape spec from the new file
    try:
        with open('shapespec.txt', 'r') as f:
            shape_spec = f.read()
    except IOError:
        sys.stderr.write("Error: Could not read shapespec.txt\n")
        sys.exit(1)

    # build the AST using ASTShaper
    shaper = ASTShaper(shape_spec)
    ast = shaper.shapetree(tree)

    # fold the constant negative number
    ast = fold_uminus(ast)

    # perform semantic checking, that would decorate the AST and catches errors
    ast = check_semantics(ast)

    # fix the quote formatting right before printing
    fix_sym_quotes(ast)

    # convert the AST to a string then strip the quotes around sym='symX'
    output = str(ast)

    # this regex looks for sym='sym...' and replaces it with sym=sym
    output = re.sub(r"sym='(sym\d+)'", r"sym=\1", output)

    # print the textual representation of the AST
    print(output)

if __name__ == '__main__':
    main()

