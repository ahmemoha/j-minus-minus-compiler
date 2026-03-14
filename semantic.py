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
        self.block_depth = 0

    def n_funcDecl(self, node):
        # entering a function: Open a new local scope
        self.symtab.open_scope()
        formals_node = node[2]
        for formal in formals_node:
            var_type = formal[0].attr
            name = formal[1].attr
            lineno = formal[1].lineno
            self.symtab.define(name, {'type': var_type, 'node': formal}, lineno)

    def n_funcDecl_exit(self, node):
        # exiting a function: Close the local scope
        self.symtab.close_scope()

    def n_mainDecl(self, node):
        self.symtab.open_scope()
        formals_node = node[2]
        for formal in formals_node:
            var_type = formal[0].attr
            name = formal[1].attr
            lineno = formal[1].lineno
            self.symtab.define(name, {'type': var_type, 'node': formal}, lineno)

    def n_mainDecl_exit(self, node):
        self.symtab.close_scope()

    def n_block(self, node):
        self.block_depth += 1

    def n_block_exit(self, node):
        self.block_depth -= 1

    def n_varDecl(self, node):
        # children: [type, id]
        lineno = node[1].lineno
        if self.block_depth > 1:
            semantic_error("local declaration not in outermost block", lineno)

        var_type = node[0].attr
        name = node[1].attr
        self.symtab.define(name, {'type': var_type, 'node': node}, lineno)

    def n_id(self, node):
        # lookup the identifier in the scope stack
        name = node.attr
        sym = self.symtab.lookup(name)
        if not sym:
            semantic_error(f"undeclared identifier '{name}'", node.lineno)
        # link the AST node directly to its symbol table entry!
        node.sym = sym

    def n_funcCall(self, node):
        # node[0] is the id node of the function being called
        if node[0].attr == 'main':
            semantic_error("main function can't be called", node[0].lineno)

# type checking
class Pass3_TypeCheck(ASTTraversal):
    def __init__(self, ast, symtab):
        super().__init__(ast)
        self.symtab = symtab

    # --- Leaf Nodes ---
    def n_number(self, node):
        node.expr_type = 'int'

    def n_true(self, node):
        node.expr_type = 'boolean'

    def n_false(self, node):
        node.expr_type = 'boolean'

    def n_string(self, node):
        node.expr_type = 'string'

    def n_id(self, node):
        # Inherit the type from the symbol table we attached in Pass 2
        if hasattr(node, 'sym') and node.sym:
            node.expr_type = node.sym['type']
        else:
            node.expr_type = 'error'

# miscellaneous checks
class Pass4_MiscChecks(ASTTraversal):
    def __init__(self, ast, symtab):
        super().__init__(ast)
        self.symtab = symtab
        self.while_depth = 0

    def n_whileStmt(self, node):
        self.while_depth += 1

    def n_whileStmt_exit(self, node):
        self.while_depth -= 1

    def n_breakStmt(self, node):
        if self.while_depth == 0:
            semantic_error("break statement outside while loop", getattr(node, 'lineno', None))

    def n_exprStmt(self, node):
        # statement expressions can only be assignments or function calls
        child = node[0]
        if child.type not in ('ASSIGN', 'funcCall'):
            semantic_error("statement expression must be assignment or function invocation", getattr(child, 'lineno', getattr(node, 'lineno', None)))

    def n_number(self, node):
        # check if 32 bit signed integer is out of bounds
        val = int(node.attr)
        if not (-2147483648 <= val <= 2147483647):
            semantic_error("integer literal out of range", node.lineno)

def check_semantics(ast):
    symtab = SymbolTable()

    Pass1_GlobalDecls(ast, symtab).postorder()
    Pass2_LocalDecls(ast, symtab).preorder()
    Pass3_TypeCheck(ast, symtab).postorder()
    Pass4_MiscChecks(ast, symtab).preorder()
    return ast
