
lexer grammar Jminus;

// J-- keywords
BOOLEAN : 'boolean';
ELSE : 'else';
FALSE : 'false';
IF : 'if';
INT : 'int';
NEW : 'new';
RETURN : 'return';
TRUE : 'true';
VOID : 'void';
WHILE : 'while';

// operators/punctuation
ASSIGN : '=';
COMMA : ',';
DIVIDE : '/';
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
INT_LIT : [0-9]+;

// supports escapes: \b, \f, \t, \r, \n, \', \", \\
STRING : '"' ( ESC | ~["\\\r\n] )* '"';

fragment ESC : '\\' [bftrn'"\\];


// letter/underscore followed by alphanumeric or underscore
ID : [a-zA-Z_] [a-zA-Z0-9_]*;

// ws
// whitespace skipping
WS : [ \t\r\n]+ -> skip ;

// skip single line comments (// to end of line)
LINE_COMMENT : '//' ~[\r\n]* -> skip;

// skip block comments
BLOCK_COMMENT : '/*' .*? '*/' -> skip;




// Catch any character that didn't match previous rules
ERR : . ;
