import sys
from cpsc411.asttraversal import ASTTraversal

class CodeGenerator(ASTTraversal):
    def __init__(self, ast, symtab):
        super().__init__(ast)
        self.symtab = symtab
        self.output = []
        self.label_counter = 0
        self.string_counter = 0

        # a simple pool of available MIPS registers
        self.free_registers = [f"$t{i}" for i in range(10)] + [f"$s{i}" for i in range(8)]

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
        # global entry point for SPIM
        self.emit("\t.text")
        self.emit("\t.globl main")
        self.emit("main:")

        # mainDecl gets L0, so we jump there
        self.emit("\tjal L0")
        self.emit("\tj Lhalt")

        # traverse the AST, the pre/post order supports entering and exiting nodes
        self.preorder()

        return "\n".join(self.output) + "\n"

    def n_mainDecl(self, node):
        main_sym = str(node[1].sym)
        main_label = self.get_new_label() # should be L0
        self.sym_to_label[main_sym] = main_label

        self.emit(f"{main_label}:")
        # allocate stack space and save return address
        self.emit("\tsubu $sp,$sp,4")
        self.emit("\tsw $ra,0($sp)")

    def n_mainDecl_exit(self, node):
        exit_label = self.get_new_label()
        self.emit(f"{exit_label}:")
        # restore return address, deallocate stack, and return
        self.emit("\tlw $ra,0($sp)")
        self.emit("\taddu $sp,$sp,4")
        self.emit("\tjr $ra")

def generate_code(ast, symtab):
    cg = CodeGenerator(ast, symtab)
    return cg.generate()
