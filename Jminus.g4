
lexer grammar Jminus;

// J-- keywords
BOOLEAN : 'boolean';
CLASS : 'class';
ELSE : 'else';
FALSE : 'false';
IF : 'if';
INT : 'int';
MAIN : 'main';
NEW : 'new';
PUBLIC : 'public';
RETURN : 'return';
STATIC : 'static';
THIS : 'this';
TRUE : 'true';
VOID : 'void';
WHILE : 'while';

// operators/punctuation
ASSIGN : '=';
COMMA : ',';
DIV : '/';
DOT : '.';
EQ : '==';
GT : '>';
LT : '<';
MINUS : '-';
MULT : '*';
NOT : '!';
NE : '!=';
PLUS : '+';
LE : '<=';
GE : '>=';
LBRACE : '{';
LBRACK : '[';
LPAREN : '(';
RBRACE : '}';
RBRACK : ']';
RPAREN : ')';
SEMI : ';';
AND : '&&';
OR : '||';



// literals and identifiers
// J-- supports base 10 integers only. Leading zeros are treated as decimal.
INT_LIT : [0-9]+



// ws and comments
// Whitespace skipping
WS : [ \t\r\n]+ -> skip ;
