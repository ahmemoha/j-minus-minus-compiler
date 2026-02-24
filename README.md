# CPSC 411: Milestone 2: J-- Parser and AST Builder

## Author
Name: Ahmed Mohamed
UCID: 30170510

## Description
This project implements a syntax analyzer, the parser, and Abstract Syntax Tree (AST) builder for the J-- language, building upon the lexical analyzer from Milestone 1. It is written in Python 3 using ANTLR4 and Prof. Aycock's `cpsc411.astshaper` library 

It reads a J-- source file, parses the grammar, and outputs a formatted textual representation of the AST to standard output. Syntax errors are safely caught and reported to standard error with a nonzero exit code. A custom post processing pass is also included to properly fold negative constant numbers

## Build Instructions
Run `make` to generate the necessary ANTLR4 lexer and parser files. 

## Usage
python3 main.py <input_file>
