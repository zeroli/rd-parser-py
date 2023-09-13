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

def tokenize_python(program):
    import tokenize
    from cStringIO import StringIO
    type_map = {
            tokenize.NUMBER: "(literal)",
            tokenize.STRING: "(literal)",
            tokenize.OP: "(operator)",
            tokenize.NAME: "(name)",
            }
    for t in tokenize.generate_tokens(StringIO(program).next):
        try:
            yield type_map[t[0]], t[1]
        except KeyError:
            if t[0] == tokenize.ENDMARKER:
                break
            else:
                raise SyntaxError("Syntax Error")
    yield "(end)", "(end)"

def tokenize(program):
    for id, value in tokenize_python(program):
        if id == "(literal)":
            symbol = symbol_table["(literal)"]
            s = symbol()
            s.value = value
        else:
            symbol = symbol_table.get(value)
            if symbol:
                s = symbol()
            elif id == "(name)":
                symbol = symbol_table[id]
                s = symbol()
                s.value = value
            else:
                raise SyntaxError("Unknown operator (%r)" % id)
        yield s

def infix(id, bp):
    def led(self, left):
        self.first = left
        self.second = expression(bp)
        return self
    symbol(id, bp).led = led


def prefix(id, bp):
    def nud(self):
        self.first = expression(bp)
        self.second = None
        return self
    symbol(id).nud = nud


def infix_r(id, bp):
    def led(self, left):
        self.first = left
        self.second = expression(bp - 1)
        return self
    symbol(id, bp).led = led

symbol("lambda", 20)
symbol("if", 20) # ternary form

infix_r("or", 30); infix_r("and", 40);
prefix("not", 50)

infix("in", 60);
#infix("not", 60) # in, not in
#infix("is", 60) # is, is not

infix("<", 60); infix("<=", 60)
infix(">", 60); infix(">=", 60)
infix("<>", 60); infix("!=", 60); infix("==", 60)

infix("|", 70); infix("^", 80); infix("&", 90)

infix("<<", 100); infix(">>", 100)

infix("+", 110); infix("-", 110)

infix("*", 120); infix("/", 120); infix("//", 120)
infix("%", 120)

prefix("-", 130); prefix("+", 130); prefix("~", 130)

infix_r("**", 140)

symbol(".", 150); symbol("[", 150); symbol("(", 150)

symbol("(literal)").nud = lambda self: self
symbol("(name)").nud = lambda self: self
symbol("(end)")

# group expression parsing
def nud(self):
    expr = expression()
    advance(")")
    return expr
symbol("(").nud = nud

def advance(id = None):
    global token
    if id and token.id != id:
        raise SyntaxError("Expected %r" % id)
    token = next()
symbol(")")

# ternary operator parsing:
# `1 if 2 else 3`
def led(self, left):
    self.first = left # consequence parsed
    self.second = expression() # parse `2` above condition
    advance("else")
    self.third = expression() # parse `3` above alternative
    return self
symbol("if").led = led
symbol("else")

# attribute lookup
# `a.b`
def led(self, left):
    global token
    if token.id != "(name)":
        raise SyntaxError("Expected an attribute name.")
    self.first = left
    self.second = token
    advance()
    return self
symbol(".").led = led

# item access
# a["x"]
def led(self, left):
    self.first = left
    self.second = expression()
    advance("]")
    return self
symbol("[").led = led
symbol("]")

def method(s):
    assert issubclass(s, symbol_base)
    def bind(fn):
        setattr(s, fn.__name__, fn)
    return bind

# function call
symbol("("); symbol(",")
@method(symbol("("))
def led(self, left):
    self.first = left
    self.second = []
    if token.id != ")":
        while 1:
            self.second.append(expression())
            if token.id != ",":
                break
            advance(",")
    advance(")")
    return self

# lambda
symbol(":")
@method(symbol("lambda"))
def nud(self):
    self.first = []
    if token.id != ":":
        argument_list(self.first)
    advance(":")
    self.second = expression()
    return self
def argument_list(list):
    while 1:
        if token.id != "(name)":
            raise SyntaxError("Expected an argument name.")
        list.append(token)
        advance()
        if token.id != ",":
            break
        advance(",")

# constants
def constant(id):
    @method(symbol(id))
    def nud(self):
        self.id = "(literal)"
        self.value = id
        return self
constant("None")
constant("True")
constant("False")

# `not in` and `is not`
@method(symbol("not", 60))
def led(self, left):
    if token.id != "in":
        raise SyntaxError("Invalid syntax")
    advance()
    self.id = "not in"
    self.first = left
    self.second = expression(60)
    return self

@method(symbol("is", 60))
def led(self, left):
    if token.id == "not":
        advance()
        self.id = "is not"
    self.first = left
    self.second = expression(60)
    return self

# tuple: `(...)`
@method(symbol("("))
def nud(self):
    self.first = []
    comma = False
    if token.id != ")":
        while 1:
            if token.id == ")":
                break
            self.first.append(expression())
            if token.id != ",":
                break
            comma = True
            advance(",")
    advance(")")
    if not self.first or comma:
        return self
    else:
        return self.first[0]

# list: `[...]`
symbol("]")

@method(symbol("["))
def nud(self):
    self.first = []
    if token.id != "]":
        while 1:
            if token.id == "]":
                break
            self.first.append(expression())
            if token.id != ",":
                break
            advance(",")
    advance("]")
    return self

symbol("}"); symbol(":")

# dict: `{k : v, ...}`
@method(symbol("{"))
def nud(self):
    self.first = []
    if token.id != "}":
        while 1:
            if token.id == "}":
                break
            self.first.append(expression())
            advance(":")
            self.first.append(expression())
            if token.id != ",":
                break
            advance(",")
    advance("}")
    return self

def parse(program):
    global token, next
    next = tokenize(program).next
    token = next()
    return expression()

if __name__ == '__main__':
    print(parse(sys.argv[1]))
