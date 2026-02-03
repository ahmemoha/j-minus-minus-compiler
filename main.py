import sys
import os
import os
from antlr4 import *
from Jminus import Jminus

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

    # have for initializing the ANTLR Lexer here
    print(f"Processing {input_path}...") 

    # success
    sys.exit(0)

if __name__ == '__main__':
    main()
