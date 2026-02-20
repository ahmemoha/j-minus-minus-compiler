import sys
import os
from antlr4 import *
from antlr4.error.ErrorListener import ErrorListener
from Jminus import Jminus


# AST shape specification for J--
# we'll build this incrementally based on ASTShaper warnings
SHAPE_SPEC = """
"""

# made a error listener to handle crashes or errors properly
class FatalErrorListener(ErrorListener):
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        sys.stderr.write(f"warning: unknown char at or near line {line}\n") # Matches the reference output format exactly
        # Don't exit, the scanner should continue trying

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

    # warning counter
    warning_count = 0

    # now have it process tokens
    token = lexer.nextToken()
    while token.type != Token.EOF:
        rule_name = lexer.symbolicNames[token.type]
        if not rule_name:
            rule_name = str(token.type)

        # handle ERR token specifically
        if rule_name == 'ERR':
            # print warning to stderr like reference compiler
            sys.stderr.write(f"warning: unknown char at or near line {token.line}\n")
            warning_count += 1
            # exit after 11 warnings to prevent flooding
            if warning_count >= 11:
                sys.stderr.write(f"error: too many warnings at or near line {token.line}\n")
                sys.exit(1)
        elif rule_name == 'BAD_ESCAPE':
            # match referencing error for bad escape in string...
            sys.stderr.write(f"error: bad escape in string at or near line {token.line}\n")
            sys.exit(1)
        elif rule_name == 'NL':
            # matches reference error for NL in string..., but also see if the text contains /r
            if '\r' in token.text:
                sys.stderr.write(f"error: CR in string at or near line {token.line}\n")
            else:
                sys.stderr.write(f"error: NL in string at or near line {token.line}\n")
            sys.exit(1)
        elif rule_name == 'UNCLOSED_STRING':
            # matches reference error for EOF in string...
            sys.stderr.write(f"error: EOF in string at or near line {token.line}\n")
            sys.exit(1)

        # valid tokens
        else:
            # the reference compiler expects the output to have escaped backslashes
            display_text = token.text.replace('\\', '\\\\')

            # escape single quotes to match the reference compiler's formatting
            display_text = display_text.replace("'", "\\'")

            # if it contains a null byte, then we should replace it
            display_text = display_text.replace('\x00', '\\x00')

            print(f"{rule_name} @ line {token.line}, attr '{display_text}'")

        token = lexer.nextToken()

    # prints the <EOF>
    print(f"<EOF> @ line {token.line}, attr '<EOF>'")

if __name__ == '__main__':
    main()

