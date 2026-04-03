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

        # LIFO pool -> popping from the end yields $s8, $s7... matching the reference
        self.free_registers = [f"$t{i}" for i in range(0, 10)] + [f"$s{i}" for i in range(0, 9)]

        # explicit tracker for active registers
        self.live_registers = []

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

        reg = self.free_registers.pop() # LIFO pop for tight register reuse
        self.live_registers.append(reg) # mark as active
        return reg

    def free_reg(self, reg):
        if reg and reg not in self.free_registers:
            self.free_registers.append(reg) # put back at the end of the stack
            if reg in self.live_registers:
                self.live_registers.remove(reg) # explicitly mark as free

    def setup_stack_frame(self, node):
        offset = 4 # 0($sp) is reserved for the return address ($ra)
        formals = [] # keep track of parameters so we can save $a0, $a1, etc.
        def find_symbols(n, is_param):
            nonlocal offset
            if hasattr(n, 'sym') and n.sym:
                sym_str = str(n.sym)
                if sym_str not in self.sym_to_label:
                    self.sym_to_label[sym_str] = f"{offset}($sp)"
                    offset += 4
                    if is_param:
                        formals.append(sym_str)

            # recursively check children without breaking on AST objects!
            if not isinstance(n, str):
                try:
                    for child in n:
                        find_symbols(child, is_param)
                except TypeError:
                    pass

        # specifically scan node[2], the formals list first to map $a0, $a1
        if len(node) > 2:
            find_symbols(node[2], True)

        # scan the rest of the function for local variables
        find_symbols(node, False)
        return offset, formals


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


        # runtime support (RTS) library
        rts_code = [
            "",
            "# --- Runtime Support (RTS) ---",
            "Lprints:",
            "\tlw $t0, 0($a0)        # load string length",
            "\taddu $t1, $a0, 4      # pointer to first char",
            "Lprints_loop:",
            "\tbeqz $t0, Lprints_done",
            "\tlb $a0, 0($t1)        # load byte into $a0",
            "\tli $v0, 11            # syscall 11: print char",
            "\tsyscall",
            "\taddu $t1, $t1, 1      # advance pointer",
            "\tsubu $t0, $t0, 1      # decrement length",
            "\tj Lprints_loop",
            "Lprints_done:",
            "\tjr $ra",
            "",
            "Lprinti:",
            "\tli $v0, 1             # syscall 1: print int",
            "\tsyscall",
            "\tjr $ra",
            "",
            "Lprintb:",
            "\tbnez $a0, Lprintb_true",
            "\t.data",
            "L_false_str: .asciiz \"false\"",
            "\t.text",
            "\tla $a0, L_false_str",
            "\tli $v0, 4             # syscall 4: print string",
            "\tsyscall",
            "\tjr $ra",
            "Lprintb_true:",
            "\t.data",
            "L_true_str: .asciiz \"true\"",
            "\t.text",
            "\tla $a0, L_true_str",
            "\tli $v0, 4             # syscall 4: print string",
            "\tsyscall",
            "\tjr $ra",
            "",
            "Lprintc:",
            "\tli $v0, 11            # syscall 11: print char",
            "\tsyscall",
            "\tjr $ra",
            "",
            "Lgetchar:",
            "\tli $v0, 12            # syscall 12: read char",
            "\tsyscall",
            "\tjr $ra",
            "",
            "Lhalt:",
            "\tli $v0, 10            # syscall 10: halt",
            "\tsyscall",
            "",
            "L_div_zero_error:",
            "\t.data",
            "\tL_div_zero_msg: .asciiz \"error: division by zero\\n\"",
            "\t.text",
            "\tla $a0, L_div_zero_msg",
            "\tli $v0, 4             # syscall 4: print string",
            "\tsyscall",
            "\tli $a0, 1             # Set the return code to 1!",
            "\tli $v0, 17            # syscall 17: exit2 (exit with code)",
            "\tsyscall"
        ]

        # combine them
        return "\n".join(entry_code + self.globals_output + self.output + rts_code) + "\n"

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
        main_label = self.sym_to_label[main_sym]

        # calculate stack frame size and save it on the node for the exit hook
        frame_size, formals = self.setup_stack_frame(node)
        node.frame_size = frame_size

        # save the exit label so return statements know where to jump
        self.current_exit_label = self.get_new_label()
        node.exit_label = self.current_exit_label

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
        frame_size, formals = self.setup_stack_frame(node)
        node.frame_size = frame_size

        # save the exit label so return statements know where to jump
        self.current_exit_label = self.get_new_label()
        node.exit_label = self.current_exit_label

        self.emit(f"{func_label}:")
        self.emit(f"\tsubu $sp,$sp,{frame_size}")
        self.emit("\tsw $ra,0($sp)")

        # emit standard MIPS argument saves: sw $a0, 4($sp); sw $a1, 8($sp); etc.
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

        # find the register buried in wrapper nodes
        def get_reg(n):
            if getattr(n, 'reg', None): return n.reg
            if not isinstance(n, str):
                try:
                    for child in n:
                        r = get_reg(child)
                        if r: return r
                except TypeError:
                    pass
            return None

        # evaluate and load arguments
        if len(node) > 1:
            actuals = node[1]
            for i in range(len(actuals)):
                arg_reg = get_reg(actuals[i])
                if arg_reg:
                    self.emit(f"\tmove $a{i},{arg_reg}")
                    self.free_reg(arg_reg) # free it so it doesn't get pushed to the stack

        # dynamic caller save for only user defined function
        is_predefined = func_sym in ['sym1', 'sym2', 'sym3', 'sym4', 'sym5', 'sym6']

        # tracker to grab active registers
        in_use = [r for r in self.live_registers]

        if in_use and not is_predefined:
            self.emit(f"\tsubu $sp,$sp,{len(in_use) * 4}")
            for i, r in enumerate(in_use):
                self.emit(f"\tsw {r},{i * 4}($sp)")

        # jump to the function
        self.emit(f"\tjal {func_label}")

        # pop all the registers back exactly as they were
        if in_use and not is_predefined:
            for i, r in enumerate(in_use):
                self.emit(f"\tlw {r},{i * 4}($sp)")
            self.emit(f"\taddu $sp,$sp,{len(in_use) * 4}")

        # capture the return value
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
        # only load variables
        # stack variables end in $sp, globals start with G
        # this completely ignores function names which start with L
        if location and location.endswith("($sp)"):
            self.emit(f"\tlw {reg},{location}") # local variable on stack
        elif location and location.startswith("G"):
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

    def n_ADD_exit(self, node): self.default_binary_op(node, "addu")
    def n_SUB_exit(self, node): self.default_binary_op(node, "subu")
    def n_MUL_exit(self, node): self.default_binary_op(node, "mul")

    def emit_div_mod_check(self, left_reg, right_reg):
        ok_label = self.get_new_label()

        # division by zero check that jumps to our RTS error block
        self.emit(f"\tbeqz {right_reg}, L_div_zero_error")

        # MIN_INT / -1 overflow Check
        temp_reg = self.alloc_reg()
        self.emit(f"\tli {temp_reg},-2147483648")
        self.emit(f"\tbne {left_reg},{temp_reg},{ok_label}")
        self.emit(f"\tli {temp_reg},-1")
        self.emit(f"\tbne {right_reg},{temp_reg},{ok_label}")

        # if we get here, it's MIN_INT / -1
        # change divisor to 1 to bypass the hardware trap
        self.emit(f"\tli {right_reg},1")
        self.emit(f"{ok_label}:")
        self.free_reg(temp_reg)

    def n_DIV_exit(self, node):
        left_reg = node[0].reg
        right_reg = node[1].reg
        res_reg = self.alloc_reg(getattr(node, 'lineno', None))

        self.emit_div_mod_check(left_reg, right_reg)
        self.emit(f"\tdiv {res_reg},{left_reg},{right_reg}")

        self.free_reg(left_reg)
        self.free_reg(right_reg)
        node.reg = res_reg

    def n_MOD_exit(self, node):
        left_reg = node[0].reg
        right_reg = node[1].reg
        res_reg = self.alloc_reg(getattr(node, 'lineno', None))

        self.emit_div_mod_check(left_reg, right_reg)
        self.emit(f"\trem {res_reg},{left_reg},{right_reg}")

        self.free_reg(left_reg)
        self.free_reg(right_reg)
        node.reg = res_reg

    # comparisons evaluate to 1, true, or 0, false
    def n_EQ_exit(self, node): self.default_binary_op(node, "seq")
    def n_NE_exit(self, node): self.default_binary_op(node, "sne")
    def n_LT_exit(self, node): self.default_binary_op(node, "slt")
    def n_GT_exit(self, node): self.default_binary_op(node, "sgt")
    def n_LE_exit(self, node): self.default_binary_op(node, "sle")
    def n_GE_exit(self, node): self.default_binary_op(node, "sge")

    def n_AND_exit(self, node): self.default_binary_op(node, "and")
    def n_OR_exit(self, node): self.default_binary_op(node, "or")
    def n_NOT_exit(self, node):
        # NOT just checks if the child evaluates to 0
        child_reg = node[0].reg
        res_reg = self.alloc_reg(getattr(node, 'lineno', None))
        self.emit(f"\tseq {res_reg},{child_reg},0")
        self.free_reg(child_reg)
        node.reg = res_reg

    def n_returnStmt_exit(self, node):
        def get_reg(n):
            if getattr(n, 'reg', None): return n.reg
            if not isinstance(n, str):
                try:
                    for child in n:
                        r = get_reg(child)
                        if r: return r
                except TypeError:
                    pass
            return None

        # because this is an _exit hook, the child, the return value, is already evaluated
        if len(node) > 0:
            ret_reg = get_reg(node[0])
            if ret_reg:
                self.emit(f"\tmove $v0,{ret_reg}")
                self.free_reg(ret_reg)

        # jump to the exit label of the function to clean up the stack
        self.emit(f"\tj {self.current_exit_label}")

    def n_TRUE_exit(self, node):
        reg = self.alloc_reg(getattr(node, 'lineno', None))
        self.emit(f"\tli {reg},1")
        node.reg = reg

    def n_FALSE_exit(self, node):
        reg = self.alloc_reg(getattr(node, 'lineno', None))
        self.emit(f"\tli {reg},0")
        node.reg = reg

    def n_true_exit(self, node): self.n_TRUE_exit(node)
    def n_false_exit(self, node): self.n_FALSE_exit(node)

    def n_exprStmt_exit(self, node):
        # this is where standalone assignments and function calls go to die
        # if they left a value in a register, we must free it so it doesn't leak
        if getattr(node[0], 'reg', None):
            self.free_reg(node[0].reg)

    def n_UMINUS_exit(self, node):
        # evaluates things like -F()
        child_reg = node[0].reg
        res_reg = self.alloc_reg(getattr(node, 'lineno', None))
        self.emit(f"\tnegu {res_reg},{child_reg}")
        self.free_reg(child_reg)
        node.reg = res_reg

def generate_code(ast, symtab):
    cg = CodeGenerator(ast, symtab)
    return cg.generate()
