import sys
from cpsc411.asttraversal import ASTTraversal

class CodeGenerator(ASTTraversal):
    def __init__(self, ast, symtab):
        super().__init__(ast)
        self.symtab = symtab
        self.output = []
        self.globals_output = []
        self.label_counter = 0
        self.string_counter = 0
        self.global_counter = 0
        self.loop_end_labels = []

        # a simple pool of available MIPS registers
        self.free_registers = [f"$s{i}" for i in range(8, -1, -1)] + [f"$t{i}" for i in range(9, -1, -1)]

        # map our semantic 'sym' IDs to MIPS labels
        self.sym_to_label = {}
        self._init_predefined_labels()

    def _init_predefined_labels(self):
        # predefined functions from the MS3 environment
        self.sym_to_label['sym1'] = 'Lprints'
        self.sym_to_label['sym2'] = 'Lprinti'
        self.sym_to_label['sym3'] = 'Lprintb'
        self.sym_to_label['sym4'] = 'Lprintc'
        self.sym_to_label['sym5'] = 'Lgetchar'
        self.sym_to_label['sym6'] = 'Lhalt'

    def alloc_reg(self, lineno=None):
        if not self.free_registers:
            sys.stderr.write(f"error: expression too complicated, ran out of registers at or near line {lineno}\n")
            sys.exit(1)
        return self.free_registers.pop(0)

    def free_reg(self, reg):
        if reg and reg not in self.free_registers:
            # put the register back into the pool to be reused
            self.free_registers.append(reg)

    def setup_stack_frame(self, node):
        offset = 4 # 0($sp) is reserved for the return address ($ra)
        # recursively search the function for variables
        def traverse(n):
            nonlocal offset
            if hasattr(n, 'sym'):
                sym_id = str(n.sym)
                # if this symbol isn't mapped yet, not a global, not a function, it's a local/parameter!
                if sym_id not in self.sym_to_label:
                    self.sym_to_label[sym_id] = f"{offset}($sp)"
                    offset += 4
            if hasattr(n, '__iter__') and not isinstance(n, str):
                for child in n:
                    traverse(child)
        traverse(node)
        return offset # this returns the total stack frame size needed

    def get_new_label(self):
        lbl = f"L{self.label_counter}"
        self.label_counter += 1
        return lbl

    def get_new_string_label(self):
        lbl = f"LS{self.string_counter}"
        self.string_counter += 1
        return lbl

    def emit(self, instr):
        self.output.append(instr)

    def pre_pass(self):
        # the global scope from MS3 is at index 1 of the symbol table stack
        global_scope = self.symtab.stack[1]
        for name, attrs in global_scope.items():
            sym_id = str(attrs['sym_id'])

            if name == 'main':
                lbl = self.get_new_label()
                self.sym_to_label[sym_id] = lbl
                self.main_label = lbl # save it for the SPIM entry point
            elif 'f(' in attrs['type']: # it's a regular function
                self.sym_to_label[sym_id] = self.get_new_label()
            else: # it's a global variable
                self.sym_to_label[sym_id] = f"G{self.global_counter}"
                self.global_counter += 1

    def generate(self):
        # pre pass, this finds all globals and functions
        self.pre_pass()

        # traverse the AST to generate code
        self.preorder()

        # build the global entry point for SPIM using the dynamically found main_label
        entry_code = [
            "\t.text",
            "\t.globl main",
            "main:",
            f"\tjal {self.main_label}",
            "\tj Lhalt"
        ]

        # combine them
        return "\n".join(entry_code + self.globals_output + self.output) + "\n"


    def preorder(self, node=None):
        if node is None:
            node = self.ast
        # if we flagged this node to be skipped (pruned), stop traversing it!
        if getattr(node, 'prune', False):
            return
        # otherwise, pass it up to the original ASTTraversal library to do its normal job
        super().preorder(node)

    def n_mainDecl(self, node):
        # prevent the traversal from trying to "load" the function name
        node[1].is_decl = True
        main_sym = str(node[1].sym)
        main_label = self.sym_to_label[main_sym] # get from pre-pass

        # calculate stack frame size and save it on the node for the exit hook
        frame_size = self.setup_stack_frame(node)
        node.frame_size = frame_size

        # save the exit label so return statements know where to jump
        self.current_exit_label = self.get_new_label()
        node.exit_label = self.current_exit_label # save it for the exit hook

        self.emit(f"{main_label}:")
        # allocate stack space and save return address
        self.emit(f"\tsubu $sp,$sp,{frame_size}")
        self.emit("\tsw $ra,0($sp)")

    def n_mainDecl_exit(self, node):
        self.emit(f"{node.exit_label}:") # use the saved label
        self.emit("\tlw $ra,0($sp)")
        self.emit(f"\taddu $sp,$sp,{node.frame_size}")
        self.emit("\tjr $ra")

    def n_string(self, node):
        raw_str = node.attr
        # evaluates safely handles escape characters like \n, \t
        evaluated_str = eval(raw_str)
        str_label = self.get_new_string_label()
        length = len(evaluated_str)

        # format the byte array for MIPS: .byte 72, 101, ...
        byte_list = ", ".join(str(ord(c)) for c in evaluated_str)

        self.emit("\t.data")
        self.emit(f"{str_label}:")
        self.emit(f"\t.word {length}")
        if byte_list:
            self.emit(f"\t.byte {byte_list}")
        self.emit("\t.align 2")
        self.emit("\t.text")

        # allocate a register and load the address of the string into it
        reg = self.alloc_reg(getattr(node, 'lineno', None))
        self.emit(f"\tla {reg},{str_label}")

        # attach the register to the node so the parent can consume it
        node.reg = reg

    def n_funcDecl(self, node):
        # prevent the traversal from trying to "load" the function name
        node[1].is_decl = True
        func_sym = str(node[1].sym)
        func_label = self.sym_to_label[func_sym]

        # calculate stack frame size and save it on the node
        frame_size = self.setup_stack_frame(node)
        node.frame_size = frame_size

        # save the exit label so return statements know where to jump
        self.current_exit_label = self.get_new_label()
        node.exit_label = self.current_exit_label # save it for the exit hook

        self.emit(f"{func_label}:")
        self.emit(f"\tsubu $sp,$sp,{frame_size}")
        self.emit("\tsw $ra,0($sp)")

        # find all parameters, formals, and save incoming registers to their stack slots
        formals = []
        def find_formals(n):
            if hasattr(n, 'type') and n.type == 'block':
                return # stop searching, we hit the body
            if hasattr(n, 'sym'):
                sym_id = str(n.sym)
                # if it's stored on the stack, it must be a parameter
                if self.sym_to_label.get(sym_id, "").endswith("($sp)") and sym_id not in formals:
                    formals.append(sym_id)
            if hasattr(n, '__iter__') and not isinstance(n, str):
                for child in n:
                    find_formals(child)

        find_formals(node)

        # emit standard MIPS argument saves: sw $a0, 4($sp); sw $a1, 8($sp)
        for i, sym in enumerate(formals):
            offset = self.sym_to_label.get(sym)
            if offset:
                self.emit(f"\tsw $a{i},{offset}")

    def n_funcDecl_exit(self, node):
        self.emit(f"{node.exit_label}:") # use the saved label
        self.emit("\tlw $ra,0($sp)")
        self.emit(f"\taddu $sp,$sp,{node.frame_size}")
        self.emit("\tjr $ra")

    def n_funcCall(self, node):
        # prune the function name of node[0] so the compiler
        # doesn't try to load the function as if it were a variable
        node[0].is_decl = True

    def n_funcCall_exit(self, node):
        func_sym = str(node[0].sym)
        func_label = self.sym_to_label.get(func_sym, "UNKNOWN_FUNC")

        # handle multiple arguments
        if len(node) > 1:
            actuals = node[1]
            for i in range(len(actuals)):
                arg_reg = getattr(actuals[i], 'reg', None)
                if arg_reg:
                    self.emit(f"\tmove $a{i},{arg_reg}")
                    self.free_reg(arg_reg)

        self.emit(f"\tjal {func_label}")

        # only allocate a register if the function actually returns something
        if getattr(node, 'sig', None) != 'void':
            ret_reg = self.alloc_reg(getattr(node, 'lineno', None))
            self.emit(f"\tmove {ret_reg},$v0")
            node.reg = ret_reg


    def n_globVarDecl(self, node):
        # prevent the traversal from evaluating the global variable name
        node[1].is_decl = True
        # node[0] is type, node[1] is id
        var_sym = str(node[1].sym)
        global_label = self.sym_to_label[var_sym]

        # send it to globals_output instead of standard output
        self.globals_output.append("\t.data")
        self.globals_output.append(f"{global_label}:")
        self.globals_output.append("\t.word 0")
        self.globals_output.append("\t.text")

    def n_varDecl(self, node):
        # local variable declarations don't generate MIPS code
        # handled by the stack frame
        node[1].is_decl = True

    def n_formal(self, node):
        # parameters don't generate MIPS code
        # handled by the stack frame
        node[1].is_decl = True

    # variables, numbers and assignments
    def n_number(self, node):
        # allocate a register and load the immediate number into it
        reg = self.alloc_reg(getattr(node, 'lineno', None))
        self.emit(f"\tli {reg},{node.attr}")
        node.reg = reg

    def n_ASSIGN(self, node):
        # tell the left child, the variable, not to load its value into a register
        # because we are about to overwrite it
        node[0].is_lvalue = True

    def n_id_exit(self, node):
        # if this is the left side of an assignment OR a declaration, do nothing!
        if getattr(node, 'is_lvalue', False) or getattr(node, 'is_decl', False):
            return

        var_sym = str(node.sym)
        location = self.sym_to_label.get(var_sym)
        # allocate a register and load the value from memory
        reg = self.alloc_reg(getattr(node, 'lineno', None))

        if location and location.endswith("($sp)"):
            self.emit(f"\tlw {reg},{location}") # local variable on stack
        elif location:
            self.emit(f"\tlw {reg},{location}") # global variable in .data

        node.reg = reg

    def n_ASSIGN_exit(self, node):
        # the right child has been evaluated into a register
        # store it
        var_sym = str(node[0].sym)
        location = self.sym_to_label.get(var_sym)
        rhs_reg = node[1].reg

        if location and location.endswith("($sp)"):
            self.emit(f"\tsw {rhs_reg},{location}")
        elif location:
            self.emit(f"\tsw {rhs_reg},{location}")

        # an assignment evaluates to its right hand side, so pass the register up
        node.reg = rhs_reg

    # if statement
    def n_ifStmt(self, node):
        node.end_label = self.get_new_label()

        # manually evaluate the condition (node[0])
        self.preorder(node[0])
        cond_reg = node[0].reg

        # emit the branch instruction! If false (0), jump to end_label
        self.emit(f"\tbeqz {cond_reg},{node.end_label}")
        self.free_reg(cond_reg)

        # prune the condition so the automatic traversal doesn't run it again
        node[0].prune = True


    def n_ifStmt_exit(self, node):
        # emit the end label after the body of the if statement
        self.emit(f"{node.end_label}:")

    def n_ifElseStmt(self, node):
        node.else_label = self.get_new_label()
        node.end_label = self.get_new_label()

        # manually evaluate the condition
        self.preorder(node[0])
        cond_reg = node[0].reg
        # branch to else_label if false
        self.emit(f"\tbeqz {cond_reg},{node.else_label}")
        self.free_reg(cond_reg)
        node[0].prune = True

        # manually evaluate the IF block (node[1])
        self.preorder(node[1])

        # jump over the ELSE block
        self.emit(f"\tj {node.end_label}")
        self.emit(f"{node.else_label}:")
        node[1].prune = True # prune the IF block so the automatic traversal just runs the ELSE block

    def n_ifElseStmt_exit(self, node):
        self.emit(f"{node.end_label}:")

    # while loop
    def n_whileStmt(self, node):
        node.start_label = self.get_new_label()
        node.end_label = self.get_new_label()
        self.loop_end_labels.append(node.end_label) # track for break statements
        self.emit(f"{node.start_label}:")

        # manually evaluate condition
        self.preorder(node[0])
        cond_reg = node[0].reg

        # branch to exit if false
        self.emit(f"\tbeqz {cond_reg},{node.end_label}")
        self.free_reg(cond_reg)
        node[0].prune = True


    def n_whileStmt_exit(self, node):
        self.emit(f"\tj {node.start_label}") # jump back to the top
        self.emit(f"{node.end_label}:")      # label to exit the loop
        self.loop_end_labels.pop()

    def n_breakStmt(self, node):
        # jump to the end label of the innermost loop
        if self.loop_end_labels:
            self.emit(f"\tj {self.loop_end_labels[-1]}")

    # for binary operators, we evaluate children, then combine them
    def default_binary_op(self, node, mips_instr):
        left_reg = node[0].reg
        right_reg = node[1].reg
        result_reg = self.alloc_reg(getattr(node, 'lineno', None))

        # for ex. add $t0, $t1, $t2 or sge $t0, $t1, $t2
        self.emit(f"\t{mips_instr} {result_reg},{left_reg},{right_reg}")
        self.free_reg(left_reg)
        self.free_reg(right_reg)
        node.reg = result_reg

    def n_ADD_exit(self, node): self.default_binary_op(node, "add")
    def n_SUB_exit(self, node): self.default_binary_op(node, "sub")
    def n_MUL_exit(self, node): self.default_binary_op(node, "mul")
    def n_DIV_exit(self, node): self.default_binary_op(node, "div")
    def n_MOD_exit(self, node): self.default_binary_op(node, "rem")

    # comparisons evaluate to 1, true, or 0, false
    def n_EQ_exit(self, node): self.default_binary_op(node, "seq")
    def n_NE_exit(self, node): self.default_binary_op(node, "sne")
    def n_LT_exit(self, node): self.default_binary_op(node, "slt")
    def n_GT_exit(self, node): self.default_binary_op(node, "sgt")
    def n_LE_exit(self, node): self.default_binary_op(node, "sle")
    def n_GE_exit(self, node): self.default_binary_op(node, "sge")


    def n_returnStmt_exit(self, node):
        # because this is an _exit hook, the child, the return value, is already evaluated
        if len(node) > 0:
            ret_reg = getattr(node[0], 'reg', None)
            if ret_reg:
                self.emit(f"\tmove $v0,{ret_reg}")
                self.free_reg(ret_reg)

        # jump to the exit label of the function to clean up the stack
        self.emit(f"\tj {self.current_exit_label}")

    def n_literal(self, node):
        if len(node) > 0:
            # check if the child is 'true', 'false', or a TRUE/FALSE token
            val = getattr(node[0], 'type', str(node[0]))
            if val in ('true', 'TRUE'):
                reg = self.alloc_reg(getattr(node, 'lineno', None))
                self.emit(f"\tli {reg},1")
                node.reg = reg
            elif val in ('false', 'FALSE'):
                reg = self.alloc_reg(getattr(node, 'lineno', None))
                self.emit(f"\tli {reg},0")
                node.reg = reg

    def n_TRUE(self, node):
        reg = self.alloc_reg(getattr(node, 'lineno', None))
        self.emit(f"\tli {reg},1")
        node.reg = reg

    def n_FALSE(self, node):
        reg = self.alloc_reg(getattr(node, 'lineno', None))
        self.emit(f"\tli {reg},0")
        node.reg = reg



def generate_code(ast, symtab):
    cg = CodeGenerator(ast, symtab)
    return cg.generate()
