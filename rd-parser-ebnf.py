# A recursive descent parser that implements an integer calculator
# with variables and conditional statements.
# the grammar is LL(1), suitable for preditive parsing.
#
# EBNF:
# <stmt>	: <assign_stmt>
# 			| <if_stmt>
#			| <cmp_expr>
#
# <assign_stmt>	: set <id> = <cmp_expr>
#
# note 'else' binds to the innermost 'if', like in c
#
# <if_stmt>	: if <comp_expr> then <stmt> [else <stmt>]
#
# <cmp_expr>	: <bitor_expr> [== <bitor expr>]
#				| <bitor_expr> [!= <bitor expr>]
#				| <bitor_expr> [>  <bitor expr>]
#				| <bitor_expr> [<  <bitor expr>]
#				| <bitor_expr> [>= <bitor expr>]
#				| <bitor_expr> [<= <bitor expr>]
#
# <bitor_expr>	: <bitxor_expr> { | <bitxor_expr> }*
#
# <bitxor_expr>	: <bitand_expr> { ^ <bitand_expr> }*
#
# <bitand_expr>	: <shift_expr>	{ & <shift_expr> }*
#
# <shift_expr>	: <arith_expr> { << <arith_expr> }*
#				| <arith_expr> { >> <arith_expr> }*
#
# <arith_expr> 	: <term> { +|- <term> }*
#
# <term>		: <power> { *|/ <power> }*
#
# <power>		: <factor> ** <power>
#				| <factor>
#
# <factor>		: <id>
#				| <number>
#				| - <factor>
#				| ( <comp_expr> )
#
# <id>			: [a-zA-Z_]\w*
# <number>		: \d+
#
# Employs EBNF and looping to solve the associativity problem in
# <term> and <arith_expr>.
# Note that <power> is defined recursively and not using EBNF
# grouping {** <factor>}. This is on purpose - as it makes the
# right-associativity of exponentation naturally expressed in the recursion
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
            | <cmp_expr>
    """
    if self.cur_token.type is None:
      return ''
    elif self.cur_token.type == 'SET':
      return self._assign_stmt()
    elif self.cur_token.type == 'IF':
      return self._if_stmt()
    else:
      return self._cmp_expr()

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
    <assign_stmt> : set <id> = <cmp_expr>
    """
    self._match('SET')
    id_name = self._match('IDENTIFIER')
    self._match('=')
    expr_val = self._cmp_expr()

    if not self.only_syntax_check:
      self.var_table[id_name] = expr_val
    return expr_val

  # <cmp_expr>    : <bitor_expr> [== <bitor_expr>]
  #               | <bitor_expr> [!= <bitor_expr>]
  #               | <bitor_expr> [> <bitor_expr>]
  #               | <bitor_expr> [< <bitor_expr>]
  #               | <bitor_expr> [>= <bitor_expr>]
  #               | <bitor_expr> [<= <bitor_expr>]
  #
  _cmp_op_map = {
    '==': operator.eq,
    '!=': operator.ne,
    '>=': operator.ge,
    '<=': operator.le,
    '>':  operator.gt,
    '<':  operator.lt,
  }
  def _cmp_expr(self):
    lval = self._bitor_expr()

    for op_name, op in self._cmp_op_map.items():
      if self.cur_token.type == op_name:
        self._match(op_name)
        return op(lval, self._bitor_expr())

    return lval

  # <bitor_expr>  : <bitxor_expr> {| <bitxor_expr>}*
  def _bitor_expr(self):
    lval = self._bitxor_expr()

    while self.cur_token.type == '|':
      self._match('|')
      lval |= self._bitxor_expr()

    return lval

  # <bitxor_expr> : <bitand_expr> {^ <bitand_expr>}*
  def _bitxor_expr(self):
    lval = self._bitand_expr()

    while self.cur_token.type == '^':
      self._match('^')
      lval ^= self._bitand_expr()

    return lval

  # <bitand_expr> : <shift_expr> {& <shift_expr>}
  def _bitand_expr(self):
    lval = self._shift_expr()

    while self.cur_token.type == '&':
      self._match('&')
      lval ^= self._shift_expr()

    return lval

  # <shift_expr>  : <arith_expr> {<< <arith_expr>}
  #               | <arith_expr> {>> <arith_expr>}
  def _shift_expr(self):
    lval = self._arith_expr()

    while self.cur_token.type in ('<<', '>>'):
      if self.cur_token.type == '<<':
        self._match('<<')
        lval <<= self._arith_expr()
      elif self.cur_token.type == '>>':
        self._match('>>')
        lval >>= self._arith_expr()

    return lval

  # <arith_expr>  : <term> {+ <term>}
  #               | <term> {- <term>}
  def _arith_expr(self):
    lval = self._term()

    while self.cur_token.type in ('+', '-'):
      if self.cur_token.type == '+':
        self._match('+')
        lval += self._term()
      elif self.cur_token.type == '-':
        self._match('-')
        lval -= self._term()

    return lval

  # <term>    : <power> {* <power>}
  #           | <power> {/ <power>}
  def _term(self):
    lval = self._power()

    while self.cur_token.type in ('*', '/'):
      if self.cur_token.type == '*':
        self._match('*')
        lval *= self._power()
      elif self.cur_token.type == '/':
        self._match('/')
        lval /= self._power()

    return lval

  # <power>   : <factor> ** <power>
  #           | <factor>
  # right associative
  def _power(self):
    lval = self._factor()

    if self.cur_token.type == '**':
      self._match('**')
      lval **= self._power()

    return lval

  # <factor>  : <id>
  #           | <number>
  #           | - <factor>
  #           | ( <cmp_expr> )
  #
  def _factor(self):
    if self.cur_token.type == '(':
      self._match('(')
      val = self._cmp_expr()
      self._match(')')
      return val
    elif self.cur_token.type == 'NUMBER':
      return int(self._match('NUMBER'))
    elif self.cur_token.type == '-':
      self._match('-')
      return -(self._factor())
    elif self.cur_token.type == 'IDENTIFIER':
      id_name = self._match('IDENTIFIER')
      if self.only_syntax_check:
        return 0
      else:
        try:
          val = self.var_table[id_name]
        except KeyError:
          self._error('Unknown identifier `{}`'.format(id_name))
        return val
    else:
      self._error('Invalid factor `{}`'.format(self.cur_token.val))


def calculator_prompt():
  print('Welcome to the calculator, Press Ctrl+C to exit.')
  cp = CalcParser()

  try:
    while True:
      try:
        line = input('--> ')
        print(cp.calc(line))
      except ParseError as err:
        print('Error:', err)
  except KeyboardInterrupt:
    print('... Thanks for using the calculator')


if __name__ == '__main__':
  import sys

  calculator_prompt()
