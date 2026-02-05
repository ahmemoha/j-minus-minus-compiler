
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
BREAK   : 'break';

// operators/punctuation
ASSIGN : '=';
COMMA : ',';
DIVIDE : '/';
EQ : '==';
GT : '>';
LT : '<';
MINUS : '-';
MULT : '*';
MODULO : '%';
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

// bad escape sequence like ab\0de
// it matches quote, valid parts, then backslash + invalid char, then rest of string, then quote
BAD_ESCAPE : '"' ( ESC | ~["\\\r\n] )* '\\' ~[bftrn'"\\\r\n] ~["\r\n]* '"';

// string contains newline that'll catch "abc\n
NL : '"' ( ESC | ~["\\\r\n] )* [\r\n];

// unclosed string at EOF, so catcing "abc
UNCLOSED_STRING : '"' ( ESC | ~["\\\r\n] )*;

// letter/underscore followed by alphanumeric or underscore
ID : [a-zA-Z_] [a-zA-Z0-9_]*;

// ws
// whitespace skipping
WS : [ \t\r\n\f]+ -> skip ;

// skip single line comments (// to end of line)
LINE_COMMENT : '//' ~[\r\n]* -> skip;

// skip block comments
BLOCK_COMMENT : '/*' .*? '*/' -> skip;




// Catch any character that didn't match previous rules
ERR : . ;
