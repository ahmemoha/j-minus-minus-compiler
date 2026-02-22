parser grammar JminusParser;

// tell ANTLR to use the tokens we defined in Milestone 1
options { tokenVocab=Jminus; }

start           : /* empty */
                | globaldeclarations
                ;

literal         : INT_LIT
                | STRING
                | TRUE
                | FALSE
                ;

type            : BOOLEAN
                | INT
                ;


globaldeclarations      : globaldeclaration
                        | globaldeclarations globaldeclaration
                        ;

// we inline the variable declaration like type identifier ';' 
// so we can shape it differently for global vs local
globaldeclaration       : type identifier ';'
                        | functiondeclaration
                        | mainfunctiondeclaration
                        ;

identifier              : ID
                        ;

functiondeclaration     : type identifier '(' formalparameterlist ')' block
                        | type identifier '(' ')' block
                        | VOID identifier '(' formalparameterlist ')' block
                        | VOID identifier '(' ')' block
                        ;

formalparameterlist     : formalparameter
                        | formalparameterlist ',' formalparameter
                        ;

formalparameter         : type identifier
                        ;

mainfunctiondeclaration : identifier '(' formalparameterlist ')' block
                        | identifier '(' ')' block
                        ;

block                   : '{' blockstatements '}'
                        | '{' '}'
                        ;

blockstatements         : blockstatement
                        | blockstatements blockstatement
                        ;

blockstatement          : type identifier ';'
                        | statement
                        ;

statement               : block
                        | ';'
                        | statementexpression ';'
                        | BREAK ';'
                        | RETURN expression ';'
                        | RETURN ';'
                        | IF '(' expression ')' statement
                        | IF '(' expression ')' statement ELSE statement
                        | WHILE '(' expression ')' statement
                        ;

statementexpression     : expression
                        ;

primary                 : literal
                        | '(' expression ')'
                        | functioninvocation
                        ;

argumentlist            : expression
                        | argumentlist ',' expression
                        ;

functioninvocation      : identifier '(' argumentlist ')'
                        | identifier '(' ')'
                        ;

postfixexpression       : primary
                        | identifier
                        ;

unaryexpression         : '-' unaryexpression
                        | '!' unaryexpression
                        | postfixexpression
                        ;

multiplicativeexpression: unaryexpression
                        | multiplicativeexpression '*' unaryexpression
                        | multiplicativeexpression '/' unaryexpression
                        | multiplicativeexpression '%' unaryexpression
                        ;

additiveexpression      : multiplicativeexpression
                        | additiveexpression '+' multiplicativeexpression
                        | additiveexpression '-' multiplicativeexpression
                        ;

relationalexpression    : additiveexpression
                        | relationalexpression '<' additiveexpression
                        | relationalexpression '>' additiveexpression
                        | relationalexpression LE additiveexpression
                        | relationalexpression GE additiveexpression
                        ;

equalityexpression      : relationalexpression
                        | equalityexpression EQ relationalexpression
                        | equalityexpression NE relationalexpression
                        ;

conditionalandexpression: equalityexpression
                        | conditionalandexpression AND equalityexpression
                        ;

conditionalorexpression : conditionalandexpression
                        | conditionalorexpression OR conditionalandexpression
                        ;

assignmentexpression    : conditionalorexpression
                        | assignment
                        ;

assignment              : identifier '=' assignmentexpression
                        ;

expression              : assignmentexpression
                        ;

