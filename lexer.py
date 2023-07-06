import re
import sys

class Token(object):
    """
    A simple token structure
    Contains the token type, value and position
    """
    def __init__(self, type, val, pos):
        self.type = type
        self.val = val
        self.pos = pos

    def __str__(self):
        return '%s(%s) at %s' % (self.type, self.val, self.pos)

class LexerError(Exception):
    """
    Lexer error exception
    pos:
        positions in the input line where the error occurred.
    """
    def __init__(self, pos):
        self.pos = pos

class Lexer(object):
    """
    A sipmle regex-based lexer/tokenizer
    See below for an example of usage.
    """
    def __init__(self, rules, skip_whitespace=True):
        """
        Create a lexer
        rules:
            a list of rules. Each rule is a `regex, type` pair,
            where `regex` is the regular repression used
            to recognize the token and `type` is the type
            of the token to return when it's recognized.

        """
        idx = 1
        regex_parts = []
        self.group_type = {}

        for regex, type in rules:
            groupname = 'GROUP%s' % idx
            regex_parts.append('(?P<%s>%s)' % (groupname, regex))
            self.group_type[groupname] = type
            idx += 1

        self.regex = re.compile('|'.join(regex_parts))
        self.re_ws_skip = re.compile('\S')
        
    def input(self, buf):
        """
        Initialize the lexer with a bufer as input.
        """
        self.buf = buf
        self.pos = 0

    def token(self):
        """
        return the next token(a Token object) found in the
        input buffer. None is returned if the end of the buffer was
        reached.
        In case of a lexing error(the current chunk of buffer matches no rule),
        a LexerError is raised with the position of the error.
        """
        if self.pos >= len(self.buf):
            return None
        else:
            m = self.re_ws_skip.search(self.buf[self.pos:])
            if m:
                self.pos += m.start()
            else:
                return None
            m = self.regex.match(self.buf[self.pos:])
            if m:
                groupname = m.lastgroup
                tok_type = self.group_type[groupname]
                tok = Token(tok_type, m.group(groupname), self.pos)
                self.pos += m.end()
                return tok

            raise LexerError(self.pos)

    def tokens(self):
        """
        returns an iterator to the tokens found in the buffer
        """
        while 1:
            tok = self.token()
            if tok is None:
                break
            yield tok

if __name__ == '__main__':
    rules = [
        ('\d+', 'NUMBER'),
        ('[a-zA-Z_]\w+', 'IDENTIFIER'),
        ('\+', 'PLUS'),
        ('\-', 'MINUS'),
        ('\*', 'MULTIPLY'),
        ('\/', 'DIVIDE'),
        ('\(', 'LP'),
        ('\)', 'RP'),
        ('=', 'EQUALS'),
    ]
    lx = Lexer(rules)

    while 1:
        line = raw_input('>>')
        if line is None:
            break
        lx.input(line)
        
        try:
            for tok in lx.tokens():
                print tok
        except LexerError, err:
            print 'LexerError at position', err.pos

