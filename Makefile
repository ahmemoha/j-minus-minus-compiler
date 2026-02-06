ANTLR_JAR = ~aycock/411/bin/cpsc411-antlr4
GRAMMAR = Jminus.g4

all:
	$(ANTLR_JAR) -Dlanguage=Python3 -no-listener -visitor $(GRAMMAR)

clean:
	rm -f Jminus.tokens Jminus.py Jminus.interp
	rm -rf __pycache__

