import re

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

    def __str__(self):
        return 'Mul(%s, %s)' % (self.l_op, self.r_op)

class Paren(Op):
    @classmethod
    def match(cls, expr):
        if expr[0] == '(' and expr[-1] == ')':
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
