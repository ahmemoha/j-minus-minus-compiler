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
// 1. Rename terminals directly (preserves attr and lineno)
'int' : int
'boolean' : bool
'void' : void
ID : id
NUMBER : num
STRING : str
'true' : true
'false' : false

// 2. Pass those renamed terminals straight up through their wrappers
type / 1 : $1
identifier / 1 : $1
literal / 1 : $1

// 3. Main Tree Structure
start / 0 : program
start / 1 : program($1)

globaldeclarations / 1 : $1
globaldeclarations / 2 : $1 +($2)

globaldeclaration / 1 : $1

variabledeclaration / 3 : globVarDecl($1, $2)

functiondeclaration / 5 with 'void' : funcDecl($1, $2, formals, $5)
functiondeclaration / 6 with 'void' : funcDecl($1, $2, formals($4), $6)
functiondeclaration / 5 with type : funcDecl($1, $2, formals, $5)
functiondeclaration / 6 with type : funcDecl($1, $2, formals($4), $6)

formalparameterlist / 1 : $1
formalparameterlist / 3 : $1 +($3)

formalparameter / 2 : formal($1, $2)

mainfunctiondeclaration / 4 : mainDecl(void, $1, formals, $4)
mainfunctiondeclaration / 5 : mainDecl(void, $1, formals($3), $5)

block / 2 : block
block / 3 : block($2)

blockstatements / 1 : $1
blockstatements / 2 : $1 +($2)

blockstatement / 1 : $1

statement / 1 with block : $1
statement / 1 with ';' : emptyStmt
statement / 2 with statementexpression : $1
statement / 2 with 'break' : breakStmt
statement / 3 with 'return' : returnStmt($2)
statement / 2 with 'return' : returnStmt
statement / 5 with 'if' : ifStmt($3, $5)
statement / 7 with 'if' : ifElseStmt($3, $5, $7)
statement / 5 with 'while' : whileStmt($3, $5)

statementexpression / 1 : $1

primary / 1 : $1
primary / 3 with '(' : $2

postfixexpression / 1 : $1

unaryexpression / 1 : $1
unaryexpression / 2 with '-' : UMINUS($2)
unaryexpression / 2 with '!' : NOT($2)

multiplicativeexpression / 1 : $1
multiplicativeexpression / 3 with '*' : MUL($1, $3)
multiplicativeexpression / 3 with '/' : DIV($1, $3)
multiplicativeexpression / 3 with '%' : MOD($1, $3)

additiveexpression / 1 : $1
additiveexpression / 3 with '+' : ADD($1, $3)
additiveexpression / 3 with '-' : SUB($1, $3)

relationalexpression / 1 : $1
relationalexpression / 3 with '<' : LT($1, $3)
relationalexpression / 3 with '>' : GT($1, $3)
relationalexpression / 3 with LE : LE($1, $3)
relationalexpression / 3 with GE : GE($1, $3)

equalityexpression / 1 : $1
equalityexpression / 3 with EQ : EQ($1, $3)
equalityexpression / 3 with NE : NE($1, $3)

conditionalandexpression / 1 : $1
conditionalandexpression / 3 with AND : AND($1, $3)

conditionalorexpression / 1 : $1
conditionalorexpression / 3 with OR : OR($1, $3)

assignmentexpression / 1 : $1

assignment / 3 : assign($1, $3)

expression / 1 : $1

argumentlist / 1 : $1
argumentlist / 3 : $1 +($3)

functioninvocation / 4 : call($1, $3)
functioninvocation / 3 : call($1)
"""

# updated error listener for Milestone 2
# made a error listener to handle crashes or errors properly
class FatalErrorListener(ErrorListener):
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        # Milestone 2 spec: Error and warning messages should go to standard error. You should exit immediately after an error message.
        sys.stderr.write(f"error: {msg} at or near line {line}\n")
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

