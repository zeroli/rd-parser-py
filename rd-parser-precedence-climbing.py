# A recursive descent parser that implements an integer calculator
# with variables and conditional statements.
#
# This parser implements exactly the same grammar as rd_parser_ebnf,
# but it evaluates expressions using a different technique.
# Instead of recursively evaluating them following the EBNF grammar,
# it uses an algorithm called precedence climbing technique
# refer to: https://www.engr.mun.ca/~theo/Misc/exp_parsing.htm
#

from __future__ import with_statement
from contextlib import contextmanager
import operator

import lexer

class ParseError(Exception): pass

class CalcParser(object):
  def __init__(self):
    lex_rules = [
      ('set',				'SET'),
      ('if',				'IF'),
      ('then',			'THEN'),
      ('else',			'ELSE'),
      ('\d+',				'NUMBER'),
      ('[a-zA-Z_]\w*', 	'IDENTIFIER'),
      ('\*\*',			'**'),
      ('!=',				'!='),
      ('==',				'=='),
      ('>=',				'>='),
      ('<=',				'<='),
      ('>>',				'>>'),
      ('<<',				'<<'),
      ('&',				'&'),
      ('\^',				'^'),
      ('\|',				'|'),
      ('<',				'<'),
      ('>',				'>'),
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

  def calc(self, line):
    print('>>parsing `{}`'.format(line))
    self.lexer.input(line)
    self._get_next_token()

    val = self._stmt()

    if self.cur_token.val != None:
      self._error('Unexpected token {} (at #{})'.format(
          self.cur_token.val, self.cur_token.pos))
    return val

  def _clear(self):
    self.cur_token = None
    self.var_table = {}
    self.only_syntax_check = False

  # Some rules are parsed with the self.only_syntax_check flag
  # turned on. This means that the syntactic structure of the
  # rules has to be checked, but no side effects are to be
  # executed. Example side effect: assignment to a variable.
  #
  # This is used, for example, when a branch of an if statement
  # is not taken (e.g. the 'else' branch of a true condition),
  # but we should still verify that the syntax is correct.
  #
  # To implement this, the syntax_check context manager can be
  # used. When a rule wants to parse some sub-rule with
  # self.only_syntax_check turned on, it can do it as follows:
  #
  # with self._syntax_check():
  #    ... parse sub-rules
  #
  # This will ensure that the only_syntax_check flag is set
  # before the sub-rules are parsed and turned off after.
  #
  @contextmanager
  def _syntax_check(self):
    # We must catch and reraise exceptions (for example,
    # ParseError can happen), but turn off the flag anyway,
    # so that subsequent statements won't be affected.
    #
    try:
      self.only_syntax_check = True
      yield
    except:
      raise
    finally:
      self.only_syntax_check = False

  def _error(self, msg):
    raise ParseError(msg)

  def _get_next_token(self):
    try:
      self.cur_token = self.lexer.token()

      if self.cur_token is None:
        self.cur_token = lexer.Token(None, None, None)
    except lexer.LexerError as e:
      self._error('Lexer error at position {}'.format(e.pos))

  def _match(self, type):
    if self.cur_token.type == type:
      val = self.cur_token.val
      self._get_next_token()
      return val
    else:
      self._error('Unmatched {} (found {})'.format(type, self.cur_token.type))

  def _stmt(self):
    """
    top level rule:
    <stmt>  : <assign_smt>
            | <if_stmt>
            | <infix_expr>
    """
    if self.cur_token.type is None:
      return ''
    elif self.cur_token.type == 'SET':
      return self._assign_stmt()
    elif self.cur_token.type == 'IF':
      return self._if_stmt()
    else:
      return self._infix_expr()

  def _if_stmt(self):
    """
    <if_stmt> : if <cmp_expr> then <stmt> [else <stmt>]
    """
    self._match('IF')
    condition = self._cmp_expr()
    self._match('THEN')

    if condition:
      # The condition is true, so we'll evaluate the 'then'
      # clause, and only syntax check the 'else' clause,
      # if there is one
      result = self._stmt()

      if self.cur_token.type == 'ELSE':
        self._match('ELSE')
        with self._syntax_check():
          self._stmt()
      return result
    else:
      # the condition is false, so we'll only syntax check
      # the 'then' clause, and evaluate the 'else' clause,
      # if there is one.
      with self._syntax_check():
        self._stmt()
      if self.cur_token.type == 'ELSE':
        self._match('ELSE')
        return self._stmt()
      else:
        return None

  def _assign_stmt(self):
    """
    <assign_stmt> : set <id> = <infix_expr>
    """
    self._match('SET')
    id_name = self._match('IDENTIFIER')
    self._match('=')
    expr_val = self._infix_expr()

    if not self.only_syntax_check:
      self.var_table[id_name] = expr_val
    return expr_val

  def _infix_expr(self):
    return self._infix_eval_expr(0)

  class Op(object):
    """
    represents an operator recognized by the infix
    evaluator. Each operator has a numeric precedence,
    and flags specifing whether it's unary/binary and
    right/left associative
    """
    def __init__(self, name, op, prec, unary=False, right_assoc=False):
      self.name = name
      self.op = op
      self.prec = prec
      self.unary = unary
      self.binary = not unary
      self.right_assoc = right_assoc
      self.left_assoc = not right_assoc

    def apply(self, *args):
      return self.op(*args)

    def isbinary(self):
      return self.binary
    
    def precedence(self):
      return self.prec
    
    def right_assoc(self):
      return self.right_assoc

    def precedes(self, other):
      if self.binary and other.binary:
        if self.prec > other.prec:
          return True
        elif self.left_assoc and (self.prec == other.prec):
          return True
      elif self.unary and other.binary:
        return self.prec >= other.prec
      
      return False

    def __repr__(self):
      return '<{}({})>'.format(self.name, self.prec)

  _ops = {
    'u-': Op('unary -', operator.neg, 90, unary=True),
    '**': Op('**', operator.pow, 70, right_assoc=True),
    '*':  Op('*', operator.mul, 50),
    '/':  Op('/', operator.div, 50),
    '+':  Op('+', operator.add, 40),
    '-':  Op('-', operator.sub, 40),
    '<<': Op('<<', operator.lshift, 35),
    '>>': Op('>>', operator.rshift, 35),
    '&':  Op('&', operator.add, 30),
    '^':  Op('^', operator.xor, 29),
    '|':  Op('|', operator.or_, 28),
    '>':  Op('>', operator.gt, 20),
    '>=': Op('>=', operator.ge, 20),
    '<':  Op('<', operator.lt, 20),
    '<=': Op('<=', operator.le, 20),
    '==': Op('==', operator.eq, 15),
    '!=': Op('!=', operator.ne, 15),
  }

  _unaries = set(['-'])

  def _infix_eval_expr(self, prec):
    lval = self._infix_eval_atom()

    # while loop to climb up one group, and then climb down
    # still check precedence: 2 + 3 * 4 + 10
    # the second '+' is still higher than `prec`?
    while (self.cur_token.type in self._ops and
          self._ops[self.cur_token.type].binary and
          self._ops[self.cur_token.type].prec >= prec):
      op = self._ops[self.cur_token.type]
      if op.right_assoc:
        # 1 ^ 2 ^ 3, for example
        # right recursion, as long as next op is >= this op precedence
        # naturally, it will be right associative
        # power := factor { ^ power }
        nprec = op.prec
      else:
        # simple add +1 to make next expr parsed(recursive call, then parsed from _infix_eval_atom)
        # to associate with next op if it has higher priority than current this `op` in its while loop
        nprec = op.prec + 1
      self._get_next_token()
      lval = op.apply(lval, self._infix_eval_expr(nprec))
 
    return lval

  def _infix_eval_atom(self):
    if self.cur_token.type in ['IDENTIFIER', 'NUMBER']:
      val = self._compute_val(self.cur_token)
      self._get_next_token()
      return val
    elif self.cur_token.type == '(':
      self._match('(')      
      val = self._infix_eval_expr(0) # restart from precedence 0
      self._match(')')
      return val
    elif self.cur_token.type in self._unaries:
      op = self._ops['u' + self.cur_token.type]
      self._get_next_token()
      return op.apply(self._infix_eval_expr(op.prec))

  def _compute_val(self, tok):
    if tok.type == 'NUMBER':
      return int(tok.val)
    elif tok.type == 'IDENTIFIER':
      if self.only_syntax_check:
        return 0
      else:
        try:
          val = self.var_table[tok.val]
        except KeyError:
          self._error('Unknown identifier `{}`'.format(tok.val))
        return val
    else:
      assert(0)

def calculator_prompt():
  print('Welcome to the calculator with precedence climbing, Press Ctrl+C to exit.')
  cp = CalcParser()

  try:
    while True:
      try:
        line = raw_input('--> ')
        print(cp.calc(line))
      except ParseError as err:
        print('Error:', err)
  except KeyboardInterrupt:
    print('... Thanks for using the calculator')


if __name__ == '__main__':
  import sys

  calculator_prompt()
