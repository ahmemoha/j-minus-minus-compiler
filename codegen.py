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
            if hasattr(n, 'type'):
                if n.type in ('varDecl', 'formal'):
                    # n[1] is the identifier node. Map it to the stack offset
                    var_sym = str(n[1].sym)
                    self.sym_to_label[var_sym] = f"{offset}($sp)"
                    offset += 4
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

    def generate(self):
        # traverse the AST first
        # this fills self.output and sets self.main_label
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


    def n_mainDecl(self, node):
        main_sym = str(node[1].sym)
        main_label = self.get_new_label() # should be L0
        self.sym_to_label[main_sym] = main_label

        # save the main label so generate() can use it later
        self.main_label = main_label

        # calculate stack frame size and save it on the node for the exit hook
        frame_size = self.setup_stack_frame(node)
        node.frame_size = frame_size

        self.emit(f"{main_label}:")
        # allocate stack space and save return address
        self.emit(f"\tsubu $sp,$sp,{frame_size}")
        self.emit("\tsw $ra,0($sp)")

    def n_mainDecl_exit(self, node):
        exit_label = self.get_new_label()
        self.emit(f"{exit_label}:")
        # restore return address, deallocate stack, and return
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
        func_sym = str(node[1].sym)
        func_label = self.get_new_label()
        self.sym_to_label[func_sym] = func_label

        # calculate stack frame size and save it on the node
        frame_size = self.setup_stack_frame(node)
        node.frame_size = frame_size

        self.emit(f"{func_label}:")
        self.emit(f"\tsubu $sp,$sp,{frame_size}")
        self.emit("\tsw $ra,0($sp)")

    def n_funcDecl_exit(self, node):
        exit_label = self.get_new_label()
        self.emit(f"{exit_label}:")
        self.emit("\tlw $ra,0($sp)")
        self.emit(f"\taddu $sp,$sp,{node.frame_size}")
        self.emit("\tjr $ra")

    def n_funcCall_exit(self, node):
        func_sym = str(node[0].sym)
        func_label = self.sym_to_label.get(func_sym, "UNKNOWN_FUNC")

        # handle arguments as node[1] is the actuals list
        if len(node) > 1 and len(node[1]) > 0:
            arg_node = node[1][0]
            arg_reg = getattr(arg_node, 'reg', None)
            if arg_reg:
                self.emit(f"\tmove $a0,{arg_reg}")
                self.free_reg(arg_reg)

        self.emit(f"\tjal {func_label}")

        # only allocate a register if the function actually returns something!
        if node.sig != 'void':
            ret_reg = self.alloc_reg(getattr(node, 'lineno', None))
            self.emit(f"\tmove {ret_reg},$v0")
            node.reg = ret_reg

    def n_globVarDecl(self, node):
        # node[0] is type, node[1] is id
        var_sym = str(node[1].sym)

        # create a unique global label like G0, G1, etc.
        global_label = f"G{self.global_counter}"
        self.global_counter += 1
        self.sym_to_label[var_sym] = global_label

        # send it to globals_output instead of standard output
        self.globals_output.append("\t.data")
        self.globals_output.append(f"{global_label}:")
        self.globals_output.append("\t.word 0")
        self.globals_output.append("\t.text")

def generate_code(ast, symtab):
    cg = CodeGenerator(ast, symtab)
    return cg.generate()
