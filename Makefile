ANTLR = ~aycock/411/bin/cpsc411-antlr4

all:
	$(ANTLR) -Dlanguage=Python3 -visitor -no-listener Jmm.g4

clean:
	rm -f JmmLexer.py Jmm.tokens Jmm.interp *.pyc
	rm -rf __pycache__
