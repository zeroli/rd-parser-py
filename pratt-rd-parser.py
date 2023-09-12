import sys
import re

def expression(rbp = 0):
    global token
    t = token
    # move over this prefix token
    token = next()

    # prefix operator expression
    left = t.nud()

    # which op left value will bind to:
    # rbp(previous/left) or token.blp(current/right)?
    while rbp < token.lbp:
        # need bind to right op
        t = token
        token = next()
        left = t.led(left)
    return left

class literal_token:
    def __init__(self, value):
        self.value = int(value)
    def nud(self):
        return self
    def __repr__(self):
        return '(literal {})'.format(self.value)

class operator_add_token:
    lbp = 10
    def nud(self):
        self.first = expression(100)
        self.second = None
        return self
    def led(self, left):
        self.first = left
        self.second = expression(self.lbp)
        return self 
    def __repr__(self):
        if self.second is not None:
            return '(add {} {})'.format(self.first, self.second)
        else:
            return '(+ {})'.format(self.first)

class operator_sub_token:
    lbp = 10
    def nud(self):
        self.first = expression(100)
        self.second = None
        return self
    def led(self, left):
        self.first = left
        self.second = expression(self.lbp)
        return self
    def __repr__(self):
        if self.second is not None:
            return '(sub {} {})'.format(self.first, self.second)
        else:
            return '(- {})'.format(self.first)

class operator_mul_token:
    lbp = 20
    def led(self, left):
        self.first = left
        self.second = expression(self.lbp)
        return self
    def __repr__(self):
        return '(mul {} {})'.format(self.first, self.second)

class operator_div_token:
    lbp = 20
    def led(self, left):
        self.first = left
        self.second = expression(self.lbp)
        return self
    def __repr__(self):
        return '(div {} {})'.format(self.first, self.second)

class operator_pow_token:
    lbp = 30
    def led(self, left):
        # right associative
        # -1 to make right op with same precedence
        # to have higher precedence
        #   ... 3 ** 2 ** 4
        # => ... 3 ** (2 ** 4)
        self.first = left
        self.second = expression(self.lbp-1)
        return self
    def __repr__(self):
        return '(pow {} {})'.format(self.first, self.second)


class end_token:
    lbp = 0

token_pat = re.compile("\s*(?:(\d+)|(\*\**|.))")

def tokenize(program):
    for number, operator in token_pat.findall(program):
        if number:
            yield literal_token(number)
        elif operator == '+':
            yield operator_add_token()
        elif operator == '-':
            yield operator_sub_token()
        elif operator == '*':
            yield operator_mul_token()
        elif operator == '/':
            yield operator_div_token()
        elif operator == '**':
            yield operator_pow_token()
        else:
            raise SyntaxError('Unknown operator')
    yield end_token()

def parse(program):
    global token, next
    next = tokenize(program).next
    token = next()
    return expression()

if __name__ == '__main__':
    print(parse(sys.argv[1]))
