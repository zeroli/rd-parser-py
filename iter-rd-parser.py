import cStringIO
import tokenize
import sys

def atom(next, token):
    if token[0] == tokenize.STRING:
        return token[1][1:-1].decode('string-escape')
    elif token[0] == tokenize.NUMBER:
        try:
            return int(token[1], 0)
        except ValueError:
            return float(token[1])
    elif token[1] == '(':
        out = []
        token = next()
        while token[1] != ')':
            out.append(atom(next, token))
            token = next()
            if token[1] == ',':
                token = next()
        return tuple(out)
    raise SyntaxError('malformed expression ({})'.format(token[1]))

def simple_eval(source):
    src = cStringIO.StringIO(source).readline

    src = tokenize.generate_tokens(src)
    return atom(src.next, src.next())

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: {} <expression>'.format(sys.argv[0]))
        sys.exit(-1)
    print(simple_eval(sys.argv[1]))
