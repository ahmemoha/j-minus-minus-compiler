import sys
from cpsc411.asttraversal import ASTTraversal

def semantic_error(msg, lineno=None):
    if lineno:
        sys.stderr.write(f"error: {msg} at or near line {lineno}\n")
    else:
        sys.stderr.write(f"error: {msg}\n")
    sys.exit(1)

class SymbolTable:
    def __init__(self):
        # the scope stack is a list of dictionaries

        # index 0 is predefined functions
        # index 1 is global declarations
        # index 2+ are local scopes
        self.stack = [{}]
        self._init_predefined_functions()
        # Open the global scope immediately
        self.open_scope()

    def _init_predefined_functions(self):
        # store the signature as 'f(arg_type)' and the return type as 'RV=return_type'
        self.stack[0]['getchar'] = {'type': 'f()', 'rv': 'int'}
        self.stack[0]['halt'] = {'type': 'f()', 'rv': 'void'}
        self.stack[0]['printb'] = {'type': 'f(boolean)', 'rv': 'void'}
        self.stack[0]['printc'] = {'type': 'f(int)', 'rv': 'void'}
        self.stack[0]['printi'] = {'type': 'f(int)', 'rv': 'void'}
        self.stack[0]['prints'] = {'type': 'f(string)', 'rv': 'void'}

    def open_scope(self):
        self.stack.append({})

    def close_scope(self):
        self.stack.pop()

    def define(self, name, attrs, lineno):
        current_scope = self.stack[-1]
        if name in current_scope:
            semantic_error(f"'{name}' redefined", lineno)
        current_scope[name] = attrs

    def lookup(self, name):
        # search from top, the local, to bottom, the predefined
        for scope in reversed(self.stack):
            if name in scope:
                return scope[name]
        return None

# global declarations
class Pass1_GlobalDecls(ASTTraversal):
    def __init__(self, ast, symtab):
        super().__init__(ast)
        self.symtab = symtab

# local scopes and identifier linking
class Pass2_LocalDecls(ASTTraversal):
    def __init__(self, ast, symtab):
        super().__init__(ast)
        self.symtab = symtab

# type checking
class Pass3_TypeCheck(ASTTraversal):
    def __init__(self, ast, symtab):
        super().__init__(ast)
        self.symtab = symtab

# miscellaneous checks
class Pass4_MiscChecks(ASTTraversal):
    def __init__(self, ast, symtab):
        super().__init__(ast)
        self.symtab = symtab

def check_semantics(ast):
    symtab = SymbolTable()
    return ast
