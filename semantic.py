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
        self.main_found = False

    def n_globVarDecl(self, node):
        # children: [type, id]
        var_type = node[0].attr
        name = node[1].attr
        lineno = node[1].lineno
        self.symtab.define(name, {'type': var_type, 'node': node}, lineno)

    def n_funcDecl(self, node):
        # children: [type, id, formals, block]
        rtype = node[0].attr
        name = node[1].attr
        lineno = node[1].lineno

        # extract parameter types to build the signature
        formals_node = node[2]
        arg_types = []
        for formal in formals_node:
            arg_types.append(formal[0].attr)

        sig = f"f({','.join(arg_types)})"

        self.symtab.define(name, {'type': sig, 'rv': rtype, 'node': node}, lineno)

    def n_mainDecl(self, node):
        # children: [void, id, formals, block]
        name = node[1].attr
        lineno = node[1].lineno

        if self.main_found:
            semantic_error("multiple main declarations found", lineno)
        self.main_found = True

        formals_node = node[2]
        if len(formals_node) > 0:
            semantic_error("main declaration can't have parameters", lineno)

        # define main in the symbol table
        self.symtab.define(name, {'type': 'f()', 'rv': 'void', 'node': node}, lineno)

    def n_program(self, node):
        # because this is a post order traversal, n_program runs LAST,
        # after all children have been evaluated.
        if not self.main_found:
            semantic_error("no main declaration found")

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

    Pass1_GlobalDecls(ast, symtab).postorder()

    return ast
