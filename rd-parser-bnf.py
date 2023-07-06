# A simpler recursive descent parser that implements an integer
# calculator. This parser suffers from an associativity problem
# due to using BNF-y recursion for rules like <term> ad <expr>
#
# BNF:
#
# <stmt>    : set <id> = <expr>
# 			| <expr>
# <expr>	: <term> + <expr>
#			| <term> - <expr>
#			| <term>
# <term>	: <factor> * <term>
# 			| <factor> / <term>
# 			| <factor>
# <factor>	: <id>
# 			| <number>
# 			| ( <expr> )
# <id>		: [a-zA-Z_]\w+
# <number>	| \d+
#
# this grammar is LL(1), suitable for predictive parsing.
#
# ------------------------------------------------------
#
#
import lexer

class ParseError(Exception): pass

class CalcParser(object):
  def __init__(self):
    lex_rules = [
      ('set',				'SET'),
      ('\d+',				'NUMBER'),
      ('[a-zA-Z_]\w*',	'IDENTIFIER'),
      ('\+',				'+'),
      ('\-',				'-'),
      ('\*',				'*'),
      ('\/',				'/'),
      ('\(',				'('),
      ('\)',				')'),
      ('=',				'='),
    ]

    self.lexer = lexer.Lexer(lex_rules)
    self._clear()

  def parse(self, line):
    """Parse a new line of input and return its result.
      Variable defiend in previous calls to parse can be
      used in following ones.

      ParseError can be raised in case of errors.
    """
    print('>>parsing: `{}`'.format(line))
    self.lexer.input(line)
    self._get_next_token()
    return self._stmt()

  def _clear(self):
    self.cur_token = None
    self.var_table = {}

  def _error(self, msg):
    raise ParseError(msg)

  def _get_next_token(self):
    try:
      self.cur_token = self.lexer.token()

      if self.cur_token is None:
        self.cur_token = lexer.Token(None, None, None)
      return self.cur_token
    except lexer.LexerError, e:
      self._error('Lexer error at position {}'.format(e.pos))

  def _match(self, type):
    """
    This `match` primitive of RD parsers.
    *verifies the current token is of the given type.
    *returns the value of the current token
    *reads in the next token
    """
    if self.cur_token is not None and self.cur_token.type == type:
      val = self.cur_token.val
      self._get_next_token()
      return val
    else:
      self._error('Unmatched {}'.format(type))

  def _stmt(self):
    """
    The top level rule of the parser.
    <stmt>	: set <id> = <expr>
        | <expr>
    """
    if self.cur_token.type == 'SET':
      self._match('SET')
      id_name = self._match('IDENTIFIER')
      self._match('=')
      expr = self._expr()

      self.var_table[id_name] = expr
      return expr
    else:
      return self._expr()

  def _expr(self):
    """
    <expr>	: <term> + <expr>
        | <term> - <expr>
        | <term>
    """
    left = self._term()

    if self.cur_token is None:
      return left

    opstr = ''
    if self.cur_token.type == '+':
      self._match('+')
      op = lambda a,b: a + b
      opstr = '+'
    elif self.cur_token.type == '-':
      self._match('-')
      op = lambda a,b: a - b
      opstr = '-'
    else:
      print('returning left = {}'.format(left))
      return left

    right = self._expr()
    print('left={} {} right={}, res={}'.format(left, opstr, right, op(left, right)))
    return op(left, right)

  def _term(self):
    """
    <term>	: <factor> * <term>
        | <factor> / <term>
        | <factor>
    """
    left = self._factor()
    if self.cur_token is None:
      return left

    opstr = ''
    if self.cur_token.type == '*':
      self._match('*')
      op = lambda a,b: a * b
      opstr = '*'
    elif self.cur_token.type == '/':
      self._match('/')
      op = lambda a,b: a / b
      opstr = '/'
    else:
      return left

    right = self._term()
    print('left={} {} right={}, res={}'.format(left, opstr, right, op(left, right)))
    return op(left, right)

  def _factor(self):
    """
    <factor>	: <id>
          | <number>
          | ( <expr> )
    """
    if self.cur_token.type == '(':
      self._match('(')
      val = self._expr()
      self._match(')')
      return val
    elif self.cur_token.type == 'NUMBER':
      return int(self._match('NUMBER'))
    elif self.cur_token.type == 'IDENTIFIER':
      id_name = self._match('IDENTIFIER')

      try:
        val = self.var_table[id_name]
      except KeyError:
        self._error('Unknown identifier `{}`'.format(id_name))
      return val
    else:
      self._error('Invalid factor `{}`'.format(self.cur_token.val))


if __name__ == '__main__':
  p = CalcParser()
  print(p.parse('5 - 1 -2'))
  print(p.parse('set x = 5'))
  print(p.parse('set y = 2 * x'))
  print(p.parse('(5 + y) * 3 + 3'))

