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
        self.next_sym_id = 1 # keep track of the global symbol counter
        self._init_predefined_functions()
        # Open the global scope immediately
        self.open_scope()

    def _init_predefined_functions(self):
        # manually assign sym1 through sym6 to predefined functions to exactly match reference
        predefs = [
            ('prints', 'f(string)', 'void'),
            ('printi', 'f(int)', 'void'),
            ('printb', 'f(bool)', 'void'),
            ('printc', 'f(int)', 'void'),
            ('getchar', 'f()', 'int'),
            ('halt', 'f()', 'void')
        ]
        for name, sig, rv in predefs:
            sym_id = f"sym{self.next_sym_id}"
            self.next_sym_id += 1
            self.stack[0][name] = {'type': sig, 'rv': rv, 'sym_id': sym_id}

    def open_scope(self):
        self.stack.append({})

    def close_scope(self):
        self.stack.pop()

    def define(self, name, attrs, lineno):
        current_scope = self.stack[-1]
        if name in current_scope:
            semantic_error(f"'{name}' redefined", lineno)

        # assign the next available sym_id to this newly defined variable/function
        sym_id = f"sym{self.next_sym_id}"
        self.next_sym_id += 1
        attrs['sym_id'] = sym_id
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

        # attach sym first, then sig
        # lookup the symbol we just defined to grab its sym_id
        node[1].sym = self.symtab.lookup(name)['sym_id']

        # add sig to the type and id nodes
        node[0].sig = var_type
        node[1].sig = var_type

    def n_funcDecl(self, node):
        # children: [type, id, formals, block]
        rtype = node[0].attr
        name = node[1].attr
        lineno = node[1].lineno

        # extract parameter types to build the signature
        formals_node = node[2]
        arg_types = [formal[0].attr for formal in formals_node]

        # map boolean to bool for the signature to match reference compiler
        sig_args = ['bool' if t == 'boolean' else t for t in arg_types]
        sig = f"f({','.join(sig_args)})"

        self.symtab.define(name, {'type': sig, 'rv': rtype, 'node': node}, lineno)

        # attach sym first, then sig
        node[1].sym = self.symtab.lookup(name)['sym_id']
        # add sig to the type and id nodes
        node[0].sig = 'bool' if rtype == 'boolean' else rtype
        node[1].sig = sig


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

        # attach sym first, then sig
        node[1].sym = self.symtab.lookup(name)['sym_id']
        # add sig to the void and id nodes
        node[0].sig = 'void'
        node[1].sig = 'f()'

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
        # Just iterate directly. The AST node is a list!
        for formal in formals_node:
            var_type = formal[0].attr
            name = formal[1].attr
            lineno = formal[1].lineno
            self.symtab.define(name, {'type': var_type, 'node': formal}, lineno)

            sig_type = 'bool' if var_type == 'boolean' else var_type
            formal[1].sym = self.symtab.lookup(name)['sym_id']
            formal.sig = sig_type
            formal[0].sig = sig_type
            formal[1].sig = sig_type


    def n_funcDecl_exit(self, node):
        # exiting a function: Close the local scope
        self.symtab.close_scope()

    # apply the same logic to mainDecl
    def n_mainDecl(self, node):
        self.symtab.open_scope()
        formals_node = node[2]
        for formal in formals_node:
            var_type = formal[0].attr
            name = formal[1].attr
            lineno = formal[1].lineno
            self.symtab.define(name, {'type': var_type, 'node': formal}, lineno)

            sig_type = 'bool' if var_type == 'boolean' else var_type
            formal[1].sym = self.symtab.lookup(name)['sym_id']
            formal.sig = sig_type
            formal[0].sig = sig_type
            formal[1].sig = sig_type

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

        sig_type = 'bool' if var_type == 'boolean' else var_type

        # attach sym first
        # attach the sym string to the identifier node
        node[1].sym = self.symtab.lookup(name)['sym_id']

        # then attch sig
        node.sig = sig_type
        node[0].sig = sig_type
        node[1].sig = sig_type

    def n_id(self, node):
        # lookup the identifier in the scope stack
        name = node.attr
        sym = self.symtab.lookup(name)
        if not sym:
            # changed from "undeclared identifier"
            semantic_error(f"unknown identifier '{name}'", node.lineno)
        # attach sym first then sig to match reference compiler formatting
        node.sym = sym['sym_id']
        node.sig = 'bool' if sym['type'] == 'boolean' else sym['type']

    def n_funcCall(self, node):
        # node[0] is the id node of the function being called
        if node[0].attr == 'main':
            # change from "main function can't be called"
            semantic_error("can't call the main function", node[0].lineno)

# type checking
class Pass3_TypeCheck(ASTTraversal):
    def __init__(self, ast, symtab):
        super().__init__(ast)
        self.symtab = symtab
        self.type_table = {
       # table driven type checking: (node_type, left_type, right_type) -> result_type
            ('ADD', 'int', 'int'): 'int',
            ('SUB', 'int', 'int'): 'int',
            ('MUL', 'int', 'int'): 'int',
            ('DIV', 'int', 'int'): 'int',
            ('MOD', 'int', 'int'): 'int',
            ('LT', 'int', 'int'): 'bool',
            ('GT', 'int', 'int'): 'bool',
            ('LE', 'int', 'int'): 'bool',
            ('GE', 'int', 'int'): 'bool',
            ('EQ', 'int', 'int'): 'bool',
            ('EQ', 'bool', 'bool'): 'bool',
            ('NE', 'int', 'int'): 'bool',
            ('NE', 'bool', 'bool'): 'bool',
            ('AND', 'bool', 'bool'): 'bool',
            ('OR', 'bool', 'bool'): 'bool',
            ('ASSIGN', 'int', 'int'): 'int',
            ('ASSIGN', 'bool', 'bool'): 'bool',
        }

    # binary operators
    def default_binary_op(self, node):
        left_type = getattr(node[0], 'sig', None)
        right_type = getattr(node[1], 'sig', None)

        result_type = self.type_table.get((node.type, left_type, right_type))
        if result_type is None:
            if left_type != 'error' and right_type != 'error':
                # map AST names back to symbols for the error message
                op_map = {
                    'ADD': '+', 'SUB': '-', 'MUL': '*', 'DIV': '/', 'MOD': '%',
                    'LT': '<', 'GT': '>', 'LE': '<=', 'GE': '>=',
                    'EQ': '==', 'NE': '!=', 'AND': '&&', 'OR': '||', 'ASSIGN': '='
                }
                op_str = op_map.get(node.type, node.type)
                # changed to "type mismatch for '+'"
                semantic_error(f"type mismatch for '{op_str}'", getattr(node, 'lineno', None))
            node.sig = 'error'
        else:
            node.sig = result_type

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
        node.sig = 'int'

    def n_true(self, node):
        node.sig = 'bool'

    def n_false(self, node):
        node.sig = 'bool'

    def n_string(self, node):
        node.sig = 'string'

    # unary operators
    def n_UMINUS(self, node):
        child_type = getattr(node[0], 'sig', None)
        if child_type != 'int':
            semantic_error("type mismatch for operator '-'", node.lineno)
        node.sig = 'int'

    def n_NOT(self, node):
        child_type = getattr(node[0], 'sig', None)
        if child_type != 'bool':
            semantic_error("type mismatch for operator '!'", node.lineno)
        node.sig = 'bool'

    # control flow
    def check_condition(self, condition_node):
        cond_type = getattr(condition_node, 'sig', None)
        if cond_type != 'bool' and cond_type != 'error':
            # changed from "condition must be of boolean type"
            semantic_error("need a boolean expression", getattr(condition_node, 'lineno', None))

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
        sym = self.symtab.lookup(id_node.attr) # lookup manually since we dropped node.sym
        if not sym:
            node.sig = 'error'
            return

        expected_sig = sym['type'] # example like 'f(int,boolean)'

        # build the actual signature from arguments
        actuals_node = node[1] if len(node) > 1 else []
        actual_types = []
        for arg in actuals_node:
            t = getattr(arg, 'sig', 'error')
            actual_types.append(t)

        actual_sig = f"f({','.join(actual_types)})"

        if expected_sig != actual_sig:
            semantic_error("number/type of arguments doesn't match function declaration", id_node.lineno)

        rv_type = sym['rv']
        node.sig = 'bool' if rv_type == 'boolean' else rv_type


# miscellaneous checks
class Pass4_MiscChecks(ASTTraversal):
    def __init__(self, ast, symtab):
        super().__init__(ast)
        self.symtab = symtab
        self.while_depth = 0

        # state tracking for returns
        self.current_func_name = None
        self.current_return_type = None
        self.found_return = False

    def n_funcDecl(self, node):
        rtype = node[0].attr
        self.current_func_name = node[1].attr
        self.current_return_type = 'bool' if rtype == 'boolean' else rtype
        self.found_return = False

    def n_funcDecl_exit(self, node):
        # triggered if there is no return statement AT ALL in a non void function
        if self.current_return_type != 'void' and not self.found_return:
            semantic_error(f"no return statement in non-void function '{self.current_func_name}'")
        self.current_func_name = None
        self.current_return_type = None

    def n_mainDecl(self, node):
        self.current_func_name = 'main'
        self.current_return_type = 'void'
        self.found_return = False

    def n_mainDecl_exit(self, node):
        self.current_func_name = None
        self.current_return_type = None

    def n_returnStmt(self, node):
        self.found_return = True
        has_return_val = len(node) > 0

        if self.current_return_type == 'void':
            if has_return_val:
                semantic_error("this function can't return a value", getattr(node, 'lineno', None))
        else:
            if not has_return_val:
                semantic_error("this function must return a value", getattr(node, 'lineno', None))
            else:
                ret_type = getattr(node[0], 'sig', None)
                if ret_type != self.current_return_type and ret_type != 'error':
                    semantic_error("returned value has the wrong type", getattr(node, 'lineno', None))

    def n_whileStmt(self, node):
        self.while_depth += 1

    def n_whileStmt_exit(self, node):
        self.while_depth -= 1

    def n_breakStmt(self, node):
        if self.while_depth == 0:
            # change from "break statement outside while loop"
            semantic_error("break must be inside 'while'", getattr(node, 'lineno', None))

    def n_exprStmt(self, node):
        # statement expressions can only be assignments or function calls
        child = node[0]
        if child.type not in ('ASSIGN', 'funcCall'):
            # change from "statement expression must be assignment or function invocation"
            semantic_error("must be assignment or function call", getattr(child, 'lineno', getattr(node, 'lineno', None)))

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
