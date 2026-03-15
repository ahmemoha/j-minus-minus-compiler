# CPSC 411: Milestone 3: J-- Semantic Analyzer

## Author
Name: Ahmed Mohamed
UCID: 30170510

## Description
This project implements a Semantic Analyzer for the J-- language, building upon the parser and AST shaper from Milestone 2. It is written in Python 3 using the provided `cpsc411.asttraversal` library.

The compiler performs four distinct AST traversals, Pre/Post order and Post order, to build a multi level Scope Stack, Symbol Table, and perform table driven type checking. It catches distinct semantic errors (stuff like type mismatches, out of bounds integers, undefined identifiers, and invalid returns) and halts with formatted error messages. Valid ASTs are dedicated with type signatures, `sig`, and symbol table references,`sym`.

## Build Instructions
Run `make` to generate the necessary ANTLR4 lexer and parser files 

## Usage
python3 main.py <input_file>
