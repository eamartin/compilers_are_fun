from __future__ import print_function
from ctypes import CFUNCTYPE, c_float
import re
from llvmlite import ir
from llvmlite import binding as llvm
import sys

llvm_float_t = ir.FloatType()
llvm.initialize()
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()

class Op(object):
    """
    Checks if string expression could be written as the operation.
    If so, returns the Op object, else returns None
    """
    @classmethod
    def match(cls, expr):
        raise NotImplementedError()

    """
    Recursively generates LLVM IR for the operation based on the input
    operations.
    """
    def codegen(self):
        raise NotImplementedError()

class Add(Op):
    def __init__(self, l_op, r_op):
        self.l_op = l_op
        self.r_op = r_op

    @classmethod
    def match(cls, expr):
        idx = naked_symbol_search(expr, ['+'])
        if idx != -1:
            l_expr = expr[:idx]
            r_expr = expr[idx + 1:]
            return cls(parse_expr(l_expr), parse_expr(r_expr))

    def codegen(self, irb):
        lval = self.l_op.codegen(irb)
        rval = self.r_op.codegen(irb)
        return irb.fadd(lval, rval)

    def __str__(self):
        return 'Add(%s, %s)' % (self.l_op, self.r_op)

class Mul(Op):
    def __init__(self, l_op, r_op):
        self.l_op = l_op
        self.r_op = r_op

    @classmethod
    def match(cls, expr):
        idx = naked_symbol_search(expr, ['*'])
        if idx != -1:
            l_expr = expr[:idx]
            r_expr = expr[idx + 1:]
            return cls(parse_expr(l_expr), parse_expr(r_expr))

    def codegen(self, irb):
        lval = self.l_op.codegen(irb)
        rval = self.r_op.codegen(irb)
        return irb.fmul(lval, rval)

    def __str__(self):
        return 'Mul(%s, %s)' % (self.l_op, self.r_op)

class Paren(Op):
    @classmethod
    def match(cls, expr):
        if expr[0] == '(' and expr[-1] == ')':
            count = 0
            for symb in expr[1:-1]:
                if symb == '(':
                    count += 1
                elif symb == ')':
                    count -= 1

                if count < 0:
                    break

            if count == 0:
                return parse_expr(expr[1:-1])

class Constant(Op):
    def __init__(self, val):
        self.val = val

    @classmethod
    def match(cls, expr):
        try:
            return cls(float(expr))
        except ValueError:
            pass

    def codegen(self, irb):
        return llvm_float_t(self.val)

    def __str__(self):
        return str(self.val)

"""
Find the first index of any symbol in targets that is not inside of any
parenthesis. Returns -1 if there is no such index.
"""
def naked_symbol_search(expr, targets):
    split_idx = -1
    paren_count = 0
    for i, sym in enumerate(expr):
        if sym == '(':
            paren_count += 1
        elif sym == ')':
            paren_count -= 1
        elif sym in targets and paren_count == 0:
            split_idx = i
            break

    return split_idx

"""
Turn an expr into an op.
"""
def parse_expr(expr):
    add_op = Add.match(expr)
    mul_op = Mul.match(expr)
    paren_op = Paren.match(expr)
    constant_op = Constant.match(expr)

    op = (Add.match(expr) or Mul.match(expr) or
          Paren.match(expr) or Constant.match(expr))

    if op is None:
        raise ValueError('Could not parse expr: "%s"' % expr)
    return op

"""
Performs a one-time clean-up of the input.
"""
def cleanup_input(inp):
    # remove all whitespaces from input for easier parsing
    return re.sub('\s+', '', inp)

"""
Copied and slightly modified from llvmlite docs.

Create an ExecutionEngine suitable for JIT code generation on
the host CPU.  The engine is reusable for an arbitrary number of
modules.
"""
def create_execution_engine():
    return llvm.create_mcjit_compiler(
        llvm.parse_assembly(''),
        llvm.Target.from_default_triple().create_target_machine()
    )

"""
Copied from llvmlite docs

Compile the LLVM IR string with the given engine.
The compiled module object is returned.
"""
def compile_ir(engine, llvm_ir):
    # Create a LLVM module object from the IR
    mod = llvm.parse_assembly(llvm_ir)
    mod.verify()
    # Now add the module and make sure it is ready for execution
    engine.add_module(mod)
    engine.finalize_object()
    return mod


def main(inp):
    # build the tree
    expr = cleanup_input(inp)
    tree = parse_expr(expr)

    # set up llvmlite IR generator
    func_name = 'compiled_func'
    func_type = ir.FunctionType(llvm_float_t, [])
    module = ir.Module(name='calculator_module')
    func = ir.Function(module, func_type, name=func_name)
    bb = func.append_basic_block(name='entry')
    irb = ir.IRBuilder(bb)

    # generate the code for the full tree
    irb.ret(tree.codegen(irb))

    engine = create_execution_engine()
    compile_ir(engine, str(module))

    func_ptr = engine.get_function_address(func_name)
    cfunc = CFUNCTYPE(c_float)(func_ptr)
    res = cfunc()

    print('%s = %s' % (expr, res))


if __name__ == '__main__':
    main(sys.argv[1])
