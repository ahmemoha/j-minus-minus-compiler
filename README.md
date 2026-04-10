# CPSC 411: Final Project: MIPS Code Generator

## Author
Name: Ahmed Mohamed
UCID: 30170510

## Description
This project implements the final backend Code Generator for the J-- language, successfully translating a decorated Abstract Syntax Tree (AST) and Symbol Table into executable MIPS assembly code. 

Building upon the semantic analyzer from Milestone 3, this compiler performs a final pass over the AST to allocate memory and emit instructions. It supports full recursive function calls, global/local scope separation, and robust trap interception.


## Build Instructions
Run `make` to generate the necessary ANTLR4 lexer and parser files.

## Usage
`python3 main.py <input_file.j--> > output.s`, then run the compiled MIPS assembly in SPIM
