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

class symbol_base(object):
    id = None # node/token type name
    value = None # used by literals
    first = second = third = None # used by tree nodes

    def nud(self):
        raise SyntaxError(
            "Syntax error (%r)." % self.id
        )

    def led(self, left):
        raise SyntaxError(
            "Unknown operator (%r)." % self.id
        )

    def __repr__(self):
        if self.id == "(name)" or self.id == "(literal)":
            return "(%s %s)" % (self.id[1:-1], self.value)
        out = [self.id, self.first, self.second, self.third]
        out = map(str, filter(None, out))
        return "(" + " ".join(out) + ")"

symbol_table = {}

def symbol(id, bp=0):
    try:
        s = symbol_table[id]
    except KeyError:
        class s(symbol_base):
            pass
        s.__name__ = "symbol-" + id # for debugging
        s.id = id
        s.lbp = bp
        symbol_table[id] = s
    else:
        s.lbp = max(bp, s.lbp)
    return s

token_pat = re.compile("\s*(?:(\d+)|(\*\**|.))")

def tokenize(program):
    for number, operator in token_pat.findall(program):
        if number:
            symbol = symbol_table["(literal)"]
            s = symbol()
            s.value = number
            yield s
        else:
            symbol = symbol_table.get(operator)
            if not symbol:
                raise SyntaxError("Unknown operator")
            yield symbol()
    symbol = symbol_table["(end)"]
    yield symbol()

def infix(id, bp):
    def led(self, left):
        self.first = left
        self.second = expression(bp)
        return self
    symbol(id, bp).led = led

infix("+", 10)
infix("-", 10)
infix("*", 20)
infix("/", 20)

def prefix(id, bp):
    def nud(self):
        self.first = expression(bp)
        self.second = None
        return self
    symbol(id).nud = nud

prefix("+", 100)
prefix("-", 100)

def infix_r(id, bp):
    def led(self, left):
        self.first = left
        self.second = expression(bp - 1)
        return self
    symbol(id, bp).led = led

infix_r("**", 30)

symbol("(literal)").nud = lambda self: self
symbol("(end)")

def parse(program):
    global token, next
    next = tokenize(program).next
    token = next()
    return expression()

if __name__ == '__main__':
    print(parse(sys.argv[1]))
