#######################################
# CONSTANTS
#######################################

RAQAMLAR = '0123456789' #digits


#######################################
# ERRORS
#######################################

class Error:
    def __init__(self, pos_start, pos_end, error_name, details):
        self.pos_start = pos_start
        self.pos_end = pos_end
        self.error_name = error_name
        self.details = details

    def as_string(self):
        result = f'{self.error_name}: {self.details}\n'
        result += f'File {self.pos_start.fn}, line {self.pos_start.ln + 1}'
        return result


class IllegalCharError(Error):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, 'Illegal Character', details)


#######################################
# POSITION
#######################################

class Position:
    def __init__(self, idx, ln, col, fn, ftxt):
        self.idx = idx
        self.ln = ln
        self.col = col
        self.fn = fn
        self.ftxt = ftxt

    def advance(self, current_char):
        self.idx += 1
        self.col += 1

        if current_char == '\n':
            self.ln += 1
            self.col = 0

        return self

    def copy(self):
        return Position(self.idx, self.ln, self.col, self.fn, self.ftxt)


#######################################
# TOKENS
#######################################

TT_RAQAM = 'RAQAM' # int
TT_SUZMOQ = 'SUZMOG'  #float
TT_QOSHISH = 'QOSHISH'  #add
TT_AJRASH= 'AJRASH' #minus
TT_KOPAYTIRMOQ = 'KOPAYTIRMOQ' #multiply
TT_BOLMOQ = 'BOLMOQ' #bolmoq
TT_OQAVS = 'OQAVS' #right parenthesis
TT_CHQAVS = 'CHQAVS' #left parenthesis
TT_EOF = 'EOF'


class Token:
    def __init__(self, type_, value=None):
        self.type = type_
        self.value = value

    def __repr__(self):
        if self.value: return f'{self.type}:{self.value}'
        return f'{self.type}'


#######################################
# LEXER
#######################################

class Lexer:
    def __init__(self, fn, text):
        self.fn = fn
        self.text = text
        self.pos = Position(-1, 0, -1, fn, text)
        self.current_char = None
        self.advance()

    def advance(self):
        self.pos.advance(self.current_char)
        self.current_char = self.text[self.pos.idx] if self.pos.idx < len(self.text) else None

    def make_tokens(self):
        tokens = []

        while self.current_char != None:
            if self.current_char in ' \t':
                self.advance()
            elif self.current_char in RAQAMLAR:
                tokens.append(self.make_number())
            elif self.current_char == '+':
                tokens.append(Token(TT_QOSHISH))
                self.advance()
            elif self.current_char == '-':
                tokens.append(Token(TT_AJRASH))
                self.advance()
            elif self.current_char == '*':
                tokens.append(Token(TT_KOPAYTIRMOQ))
                self.advance()
            elif self.current_char == '/':
                tokens.append(Token(TT_BOLMOQ))
                self.advance()
            elif self.current_char == '(':
                tokens.append(Token(TT_OQAVS))
                self.advance()
            elif self.current_char == ')':
                tokens.append(Token(TT_CHQAVS))
                self.advance()
            else:
                pos_start = self.pos.copy()
                char = self.current_char
                self.advance()
                return [], IllegalCharError(pos_start, self.pos, "'" + char + "'")

        return tokens, None

    def make_number(self):
        num_str = ''
        dot_count = 0

        while self.current_char != None and self.current_char in RAQAMLAR + '.':
            if self.current_char == '.':
                if dot_count == 1: break
                dot_count += 1
                num_str += '.'
            else:
                num_str += self.current_char
            self.advance()

        if dot_count == 0:
            return Token(TT_RAQAM, int(num_str))
        else:
            return Token(TT_SUZMOQ, float(num_str))


#######################################
# PARSER
#######################################

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.tok_idx = -1
        self.advance()

    def advance(self, ):
        self.tok_idx += 1
        if self.tok_idx < len(self.tokens):
            self.current_tok = self.tokens[self.tok_idx]
        return self.current_tok

    def parse(self):
        res = self.expr()
        if not res.error and self.current_tok.type != TT_EOF:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected '+', '-', '*' or '/'"
            ))
        return res

    ###################################

    def factor(self):
        res = ParseResult()
        tok = self.current_tok

        if tok.type in (TT_QOSHISH, TT_AJRASH):
            res.register(self.advance())
            factor = res.register(self.factor())
            if res.error: return res
            return res.success(UnaryOpNode(tok, factor))

        elif tok.type in (TT_RAQAM, TT_SUZMOQ):
            res.register(self.advance())
            return res.success(NumberNode(tok))

        elif tok.type == TT_CHQAVS:
            res.register(self.advance())
            expr = res.register(self.expr())
            if res.error: return res
            if self.current_tok.type == TT_OQAVS:
                res.register(self.advance())
                return res.success(expr)
            else:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    "Expected ')'"
                ))

        return res.failure(InvalidSyntaxError(
            tok.pos_start, tok.pos_end,
            "Expected int or float"
        ))

    def term(self):
        return self.bin_op(self.factor, (TT_MUL, TT_DIV))

    def expr(self):
        return self.bin_op(self.term, (TT_PLUS, TT_MINUS))

    ###################################

    def bin_op(self, func, ops):
        res = ParseResult()
        left = res.register(func())
        if res.error: return res

        while self.current_tok.type in ops:
            op_tok = self.current_tok
            res.register(self.advance())
            right = res.register(func())
            if res.error: return res
            left = BinOpNode(left, op_tok, right)

        return res.success(left)


#######################################
# RUN
#######################################

def run(fn, text):
    #Generate tokens
    lexer = Lexer(fn, text)
    tokens, error = lexer.make_tokens()

    if error: return None, error
    # Generate AST
    parser = Parser(tokens)
    ast = parser.parse()

    return ast.node, ast.error
