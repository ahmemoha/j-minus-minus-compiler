ANTLR_JAR = ~aycock/411/bin/cpsc411-antlr4
LEXER_GRAMMAR = Jminus.g4
PARSER_GRAMMAR = JminusParser.g4

all:
	$(ANTLR_JAR) -Dlanguage=Python3 -no-listener -visitor $(LEXER_GRAMMAR)
	$(ANTLR_JAR) -Dlanguage=Python3 -no-listener -visitor $(PARSER_GRAMMAR)

clean:
	rm -f Jminus.tokens Jminus.py Jminus.interp
	rm -f JminusParser.tokens JminusParser.py JminusParserVisitor.py JminusParser.interp
	rm -rf __pycache__ *.pyc

