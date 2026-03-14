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
        # add sig to the type and id nodes
        node[0].sig = var_type
        node[1].sig = var_type
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

        # map boolean to bool for the signature to match reference compiler
        sig_args = ['bool' if t == 'boolean' else t for t in arg_types]
        sig = f"f({','.join(sig_args)})"

        # add sig to the type and id nodes
        node[0].sig = 'bool' if rtype == 'boolean' else rtype
        node[1].sig = sig

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

        # add sig to the void and id nodes
        node[0].sig = 'void'
        node[1].sig = 'f()'

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
            # add sig to formal node, its type, and its id
            formal.sig = 'bool' if var_type == 'boolean' else var_type
            formal[0].sig = 'bool' if var_type == 'boolean' else var_type
            formal[1].sig = 'bool' if var_type == 'boolean' else var_type
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
            formal.sig = 'bool' if var_type == 'boolean' else var_type
            formal[0].sig = 'bool' if var_type == 'boolean' else var_type
            formal[1].sig = 'bool' if var_type == 'boolean' else var_type
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
        # add sig to varDecl, type, and id
        sig_type = 'bool' if var_type == 'boolean' else var_type
        node.sig = sig_type
        node[0].sig = sig_type
        node[1].sig = sig_type

        self.symtab.define(name, {'type': var_type, 'node': node}, lineno)

    def n_id(self, node):
        # lookup the identifier in the scope stack
        name = node.attr
        sym = self.symtab.lookup(name)
        if not sym:
            semantic_error(f"undeclared identifier '{name}'", node.lineno)
        # instead of attaching the whole dictionary we just add the sig
        sig_type = 'bool' if sym['type'] == 'boolean' else sym['type']
        node.sig = sig_type

    def n_funcCall(self, node):
        # node[0] is the id node of the function being called
        if node[0].attr == 'main':
            semantic_error("main function can't be called", node[0].lineno)

# type checking
class Pass3_TypeCheck(ASTTraversal):
    def __init__(self, ast, symtab):
        super().__init__(ast)
        self.symtab = symtab
        self.current_function_return_type = None
        self.type_table = { ... } # keep existing table


    # table driven type checking: (node_type, left_type, right_type) -> result_type
        self.type_table = {
            ('ADD', 'int', 'int'): 'int',
            ('SUB', 'int', 'int'): 'int',
            ('MUL', 'int', 'int'): 'int',
            ('DIV', 'int', 'int'): 'int',
            ('MOD', 'int', 'int'): 'int',
            ('LT', 'int', 'int'): 'boolean',
            ('GT', 'int', 'int'): 'boolean',
            ('LE', 'int', 'int'): 'boolean',
            ('GE', 'int', 'int'): 'boolean',
            ('EQ', 'int', 'int'): 'boolean',
            ('EQ', 'boolean', 'boolean'): 'boolean',
            ('NE', 'int', 'int'): 'boolean',
            ('NE', 'boolean', 'boolean'): 'boolean',
            ('AND', 'boolean', 'boolean'): 'boolean',
            ('OR', 'boolean', 'boolean'): 'boolean',
            ('ASSIGN', 'int', 'int'): 'int',
            ('ASSIGN', 'boolean', 'boolean'): 'boolean',
        }

    # binary operators
    def default_binary_op(self, node):
        left_type = getattr(node[0], 'expr_type', None)
        right_type = getattr(node[1], 'expr_type', None)

        result_type = self.type_table.get((node.type, left_type, right_type))
        if result_type is None:
            if left_type != 'error' and right_type != 'error':
                semantic_error(f"type mismatch for operator '{node.type}'", getattr(node, 'lineno', None))
            node.expr_type = 'error'
        else:
            node.expr_type = result_type

    def n_ADD(self, node): self.default_binary_op(node)
    def n_SUB(self, node): self.default_binary_op(node)
    def n_MUL(self, node): self.default_binary_op(node)
    def n_DIV(self, node): self.default_binary_op(node)
    def n_MOD(self, node): self.default_binary_op(node)
    def n_LT(self, node): self.default_binary_op(node)
    def n_GT(self, node): self.default_binary_op(node)
    def n_LE(self, node): self.default_binary_op(node)
    def n_GE(self, node): self.default_binary_op(node)
    def n_EQ(self, node): self.default_binary_op(node)
    def n_NE(self, node): self.default_binary_op(node)
    def n_AND(self, node): self.default_binary_op(node)
    def n_OR(self, node): self.default_binary_op(node)
    def n_ASSIGN(self, node): self.default_binary_op(node)

    # leaf nodes
    def n_number(self, node):
        node.expr_type = 'int'

    def n_true(self, node):
        node.expr_type = 'boolean'

    def n_false(self, node):
        node.expr_type = 'boolean'

    def n_string(self, node):
        node.expr_type = 'string'

    def n_id(self, node):
        # inherit the type from the symbol table we attached in pass 2
        if hasattr(node, 'sym') and node.sym:
            node.expr_type = node.sym['type']
        else:
            node.expr_type = 'error'

    # unary operators
    def n_UMINUS(self, node):
        child_type = getattr(node[0], 'expr_type', None)
        if child_type != 'int':
            semantic_error("type mismatch for operator '-'", node.lineno)
        node.expr_type = 'int'

    def n_NOT(self, node):
        child_type = getattr(node[0], 'expr_type', None)
        if child_type != 'boolean':
            semantic_error("type mismatch for operator '!'", node.lineno)
        node.expr_type = 'boolean'

    # control flow
    def check_condition(self, condition_node):
        cond_type = getattr(condition_node, 'expr_type', None)
        if cond_type != 'boolean' and cond_type != 'error':
            semantic_error("condition must be of boolean type", getattr(condition_node, 'lineno', None))

    def n_ifStmt(self, node):
        self.check_condition(node[0])

    def n_ifElseStmt(self, node):
        self.check_condition(node[0])

    def n_whileStmt(self, node):
        # the whileStmt in the AST has condition at index 0
        self.check_condition(node[0])

    # function calls
    def n_funcCall(self, node):
        id_node = node[0]
        sym = getattr(id_node, 'sym', None)
        if not sym:
            node.expr_type = 'error'
            return

        expected_sig = sym['type'] # example like 'f(int,boolean)'

        # build the actual signature from arguments
        actuals_node = node[1] if len(node) > 1 else []
        actual_types = []
        for arg in actuals_node:
            t = getattr(arg, 'expr_type', 'error')
            actual_types.append(t)

        actual_sig = f"f({','.join(actual_types)})"

        if expected_sig != actual_sig:
            semantic_error("number/type of arguments doesn't match function declaration", id_node.lineno)

        node.expr_type = sym['rv']

    # track current function context for return checks
    def n_funcDecl(self, node):
        self.current_function_return_type = node[0].attr

    def n_funcDecl_exit(self, node):
        self.current_function_return_type = None

    def n_mainDecl(self, node):
        self.current_function_return_type = 'void'

    def n_mainDecl_exit(self, node):
        self.current_function_return_type = None

    # returns
    def n_returnStmt(self, node):
        # if there is a return value, it's at node[0]
        # therwise no children
        has_return_val = len(node) > 0

        if self.current_function_return_type == 'void':
            if has_return_val:
                semantic_error("void function can't return a value", getattr(node, 'lineno', None))
        else:
            if not has_return_val:
                semantic_error("non-void function must return a value", getattr(node, 'lineno', None))
            else:
                ret_type = getattr(node[0], 'expr_type', None)
                if ret_type != self.current_function_return_type and ret_type != 'error':
                    semantic_error("return value has wrong type", getattr(node, 'lineno', None))


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
