'''!/usr/bin/env python3
"""
Thunder Hackathon 2.0 - JavaScript Runtime in Python
A clean implementation of a JS interpreter: Lexer -> Parser -> Evaluator
"""
'''
import sys
import math
import re
import time
from typing import Any, List, Dict, Optional, Tuple


# ─────────────────────────────────────────────
#  LEXER
# ─────────────────────────────────────────────

TT = {
    'NUM': 'NUMBER', 'STR': 'STRING', 'BOOL': 'BOOL', 'NULL': 'NULL',
    'UNDEFINED': 'UNDEFINED', 'IDENT': 'IDENT', 'KEYWORD': 'KEYWORD',
    'OP': 'OP', 'LPAREN': '(', 'RPAREN': ')', 'LBRACE': '{',
    'RBRACE': '}', 'LBRACKET': '[', 'RBRACKET': ']', 'COMMA': ',',
    'SEMI': ';', 'COLON': ':', 'DOT': '.', 'EOF': 'EOF',
    'SPREAD': '...', 'ARROW': '=>',
}

KEYWORDS = {
    'let', 'const', 'var', 'function', 'return', 'if', 'else',
    'for', 'while', 'do', 'break', 'continue', 'new', 'typeof',
    'instanceof', 'in', 'of', 'switch', 'case', 'default', 'throw',
    'try', 'catch', 'finally', 'delete', 'void', 'class', 'this',
    'super', 'import', 'export',
}

class Token:
    __slots__ = ('type', 'value')
    def __init__(self, type_, value):
        self.type = type_
        self.value = value
    def __repr__(self):
        return f'Token({self.type}, {self.value!r})'

class LexError(Exception): pass

def tokenize(src: str) -> List[Token]:
    tokens: List[Token] = []
    i = 0
    n = len(src)

    def peek(offset=0):
        j = i + offset
        return src[j] if j < n else ''

    while i < n:
        c = src[i]

        # whitespace
        if c in ' \t\r\n':
            i += 1
            continue

        # line comment
        if c == '/' and peek(1) == '/':
            while i < n and src[i] != '\n':
                i += 1
            continue

        # block comment
        if c == '/' and peek(1) == '*':
            i += 2
            while i < n - 1 and not (src[i] == '*' and src[i+1] == '/'):
                i += 1
            i += 2
            continue

        # spread operator
        if c == '.' and peek(1) == '.' and peek(2) == '.':
            tokens.append(Token(TT['SPREAD'], '...'))
            i += 3
            continue

        # numbers (hex 0x, octal 0o, binary 0b, decimal, float, scientific)
        if c.isdigit() or (c == '.' and peek(1).isdigit()):
            j = i
            # hex
            if c == '0' and i + 1 < n and src[i+1] in 'xX':
                i += 2
                while i < n and src[i] in '0123456789abcdefABCDEF':
                    i += 1
                tokens.append(Token(TT['NUM'], float(int(src[j:i], 16))))
                continue
            # octal
            if c == '0' and i + 1 < n and src[i+1] in 'oO':
                i += 2
                while i < n and src[i] in '01234567':
                    i += 1
                tokens.append(Token(TT['NUM'], float(int(src[j:i], 8))))
                continue
            # binary
            if c == '0' and i + 1 < n and src[i+1] in 'bB':
                i += 2
                while i < n and src[i] in '01':
                    i += 1
                tokens.append(Token(TT['NUM'], float(int(src[j:i], 2))))
                continue
            # decimal / float
            while i < n and (src[i].isdigit() or src[i] == '.'):
                i += 1
            # scientific notation
            if i < n and src[i] in 'eE':
                i += 1
                if i < n and src[i] in '+-':
                    i += 1
                while i < n and src[i].isdigit():
                    i += 1
            tokens.append(Token(TT['NUM'], float(src[j:i])))
            continue

        # strings
        if c in ('"', "'", '`'):
            quote = c
            i += 1
            j = i
            parts = []
            buf = ''
            while i < n and src[i] != quote:
                if src[i] == '\\':
                    i += 1
                    esc = {'n': '\n', 't': '\t', 'r': '\r', '"': '"',
                           "'": "'", '\\': '\\', '`': '`', '0': '\0'}
                    buf += esc.get(src[i], src[i])
                    i += 1
                elif quote == '`' and src[i] == '$' and peek(1) == '{':
                    # template literal expression
                    parts.append(('str', buf))
                    buf = ''
                    i += 2  # skip ${
                    depth = 1
                    expr_start = i
                    while i < n and depth > 0:
                        if src[i] == '{': depth += 1
                        elif src[i] == '}': depth -= 1
                        i += 1
                    expr_code = src[expr_start:i-1]
                    parts.append(('expr', expr_code))
                else:
                    buf += src[i]
                    i += 1
            i += 1  # closing quote
            if parts or quote == '`':
                parts.append(('str', buf))
                tokens.append(Token('TEMPLATE', parts))
            else:
                tokens.append(Token(TT['STR'], buf))
            continue

        # identifiers / keywords
        if c.isalpha() or c in '_$':
            j = i
            while i < n and (src[i].isalnum() or src[i] in '_$'):
                i += 1
            word = src[j:i]
            if word == 'true':
                tokens.append(Token(TT['BOOL'], True))
            elif word == 'false':
                tokens.append(Token(TT['BOOL'], False))
            elif word == 'null':
                tokens.append(Token(TT['NULL'], None))
            elif word == 'undefined':
                tokens.append(Token(TT['UNDEFINED'], None))
            elif word in KEYWORDS:
                tokens.append(Token(TT['KEYWORD'], word))
            else:
                tokens.append(Token(TT['IDENT'], word))
            continue

        # operators (multi-char first)
        multi_ops = [
            '===', '!==', '=>', '**', '++', '--', '+=', '-=', '*=', '/=',
            '%=', '**=', '<=', '>=', '==', '!=', '&&', '||', '??', '<<',
            '>>', '>>>', '?.', '!', '~',
        ]
        matched = False
        for op in multi_ops:
            if src[i:i+len(op)] == op:
                tokens.append(Token(TT['OP'], op))
                i += len(op)
                matched = True
                break
        if matched:
            continue

        single = {
            '(': TT['LPAREN'], ')': TT['RPAREN'],
            '{': TT['LBRACE'], '}': TT['RBRACE'],
            '[': TT['LBRACKET'], ']': TT['RBRACKET'],
            ',': TT['COMMA'], ';': TT['SEMI'],
            ':': TT['COLON'], '.': TT['DOT'],
        }
        if c in single:
            tokens.append(Token(single[c], c))
            i += 1
            continue

        if c in '+-*/%<>=&|^?!~':
            tokens.append(Token(TT['OP'], c))
            i += 1
            continue

        raise LexError(f"Unknown character: {c!r} at pos {i}")

    tokens.append(Token(TT['EOF'], None))
    return tokens


# ─────────────────────────────────────────────
#  AST NODES (simple dicts for speed)
# ─────────────────────────────────────────────

def node(kind, **kw):
    return {'kind': kind, **kw}


# ─────────────────────────────────────────────
#  PARSER
# ─────────────────────────────────────────────

class ParseError(Exception): pass

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self, offset=0):
        return self.tokens[min(self.pos + offset, len(self.tokens) - 1)]

    def cur(self):
        return self.tokens[self.pos]

    def eat(self, type_=None, value=None):
        t = self.tokens[self.pos]
        if type_ and t.type != type_:
            raise ParseError(f"Expected type {type_!r}, got {t.type!r} ({t.value!r}) at pos {self.pos}")
        if value and t.value != value:
            raise ParseError(f"Expected {value!r}, got {t.value!r}")
        self.pos += 1
        return t

    def eat_semi(self):
        if self.cur().type == TT['SEMI']:
            self.eat(TT['SEMI'])

    def match(self, type_=None, value=None):
        t = self.cur()
        if type_ and t.type != type_:
            return False
        if value and t.value != value:
            return False
        return True

    # ── Program ──────────────────────────────

    def parse(self):
        body = []
        while not self.match(TT['EOF']):
            body.append(self.parse_stmt())
        return node('Program', body=body)

    # ── Statements ───────────────────────────

    def parse_stmt(self):
        t = self.cur()

        if t.type == TT['KEYWORD']:
            v = t.value
            if v in ('let', 'const', 'var'):
                return self.parse_var_decl()
            if v == 'function':
                return self.parse_func_decl()
            if v == 'return':
                return self.parse_return()
            if v == 'if':
                return self.parse_if()
            if v == 'for':
                return self.parse_for()
            if v == 'while':
                return self.parse_while()
            if v == 'do':
                return self.parse_do_while()
            if v == 'break':
                self.eat()
                self.eat_semi()
                return node('Break')
            if v == 'continue':
                self.eat()
                self.eat_semi()
                return node('Continue')
            if v == 'throw':
                self.eat()
                expr = self.parse_expr()
                self.eat_semi()
                return node('Throw', expr=expr)
            if v == 'try':
                return self.parse_try()
            if v == 'switch':
                return self.parse_switch()
            if v == 'class':
                return self.parse_class()

        if t.type == TT['LBRACE']:
            return self.parse_block()

        if t.type == TT['SEMI']:
            self.eat()
            return node('Empty')

        # expression statement
        expr = self.parse_expr()
        self.eat_semi()
        return node('ExprStmt', expr=expr)

    def parse_block(self):
        self.eat(TT['LBRACE'])
        body = []
        while not self.match(TT['RBRACE']):
            if self.match(TT['EOF']): break
            body.append(self.parse_stmt())
        self.eat(TT['RBRACE'])
        return node('Block', body=body)

    def parse_var_decl(self):
        kind = self.eat(TT['KEYWORD']).value  # let/const/var
        declarations = []
        while True:
            # destructuring
            if self.match(TT['LBRACKET']):
                pattern = self.parse_array_pattern()
                init = None
                if self.match(TT['OP'], '='):
                    self.eat()
                    init = self.parse_assign_expr()
                declarations.append(node('Declarator', id=pattern, init=init, destructure='array'))
            elif self.match(TT['LBRACE']):
                pattern = self.parse_object_pattern()
                init = None
                if self.match(TT['OP'], '='):
                    self.eat()
                    init = self.parse_assign_expr()
                declarations.append(node('Declarator', id=pattern, init=init, destructure='object'))
            else:
                name = self.eat(TT['IDENT']).value
                init = None
                if self.match(TT['OP'], '='):
                    self.eat()
                    init = self.parse_assign_expr()
                declarations.append(node('Declarator', id=name, init=init, destructure=None))
            if self.match(TT['COMMA']):
                self.eat()
            else:
                break
        self.eat_semi()
        return node('VarDecl', decl_kind=kind, declarations=declarations)

    def parse_array_pattern(self):
        self.eat(TT['LBRACKET'])
        names = []
        while not self.match(TT['RBRACKET']):
            if self.match(TT['COMMA']):
                names.append(None)  # hole
                self.eat()
            elif self.cur().type == TT['SPREAD']:
                self.eat()
                names.append(('rest', self.eat(TT['IDENT']).value))
                break
            else:
                names.append(self.eat(TT['IDENT']).value)
                if self.match(TT['COMMA']): self.eat()
        self.eat(TT['RBRACKET'])
        return names

    def parse_object_pattern(self):
        self.eat(TT['LBRACE'])
        keys = []
        while not self.match(TT['RBRACE']):
            key = self.eat(TT['IDENT']).value
            alias = key
            if self.match(TT['COLON']):
                self.eat()
                alias = self.eat(TT['IDENT']).value
            keys.append((key, alias))
            if self.match(TT['COMMA']): self.eat()
        self.eat(TT['RBRACE'])
        return keys

    def parse_func_decl(self):
        self.eat(TT['KEYWORD'], 'function')
        name = self.eat(TT['IDENT']).value
        params, rest_param = self.parse_params()
        body = self.parse_block()
        return node('FuncDecl', name=name, params=params, rest_param=rest_param, body=body)

    def parse_params(self):
        self.eat(TT['LPAREN'])
        params = []
        rest_param = None
        while not self.match(TT['RPAREN']):
            if self.cur().type == TT['SPREAD']:
                self.eat()
                rest_param = self.eat(TT['IDENT']).value
                break
            name = self.eat(TT['IDENT']).value
            default = None
            if self.match(TT['OP'], '='):
                self.eat()
                default = self.parse_assign_expr()
            params.append((name, default))
            if self.match(TT['COMMA']): self.eat()
        self.eat(TT['RPAREN'])
        return params, rest_param

    def parse_return(self):
        self.eat(TT['KEYWORD'], 'return')
        val = None
        if not self.match(TT['SEMI']) and not self.match(TT['RBRACE']) and not self.match(TT['EOF']):
            val = self.parse_expr()
        self.eat_semi()
        return node('Return', value=val)

    def parse_if(self):
        self.eat(TT['KEYWORD'], 'if')
        self.eat(TT['LPAREN'])
        test = self.parse_expr()
        self.eat(TT['RPAREN'])
        consequent = self.parse_stmt()
        alternate = None
        if self.match(TT['KEYWORD'], 'else'):
            self.eat()
            alternate = self.parse_stmt()
        return node('If', test=test, consequent=consequent, alternate=alternate)

    def parse_for(self):
        self.eat(TT['KEYWORD'], 'for')
        self.eat(TT['LPAREN'])

        # for...of / for...in detection
        if self.cur().type == TT['KEYWORD'] and self.cur().value in ('let', 'const', 'var'):
            saved = self.pos
            kind = self.eat(TT['KEYWORD']).value
            var_name = None
            if self.cur().type == TT['IDENT']:
                var_name = self.eat(TT['IDENT']).value
            if self.match(TT['KEYWORD'], 'of'):
                self.eat()
                iterable = self.parse_expr()
                self.eat(TT['RPAREN'])
                body = self.parse_stmt()
                return node('ForOf', decl_kind=kind, var=var_name, iterable=iterable, body=body)
            if self.match(TT['KEYWORD'], 'in'):
                self.eat()
                obj = self.parse_expr()
                self.eat(TT['RPAREN'])
                body = self.parse_stmt()
                return node('ForIn', decl_kind=kind, var=var_name, obj=obj, body=body)
            self.pos = saved

        init = None
        if not self.match(TT['SEMI']):
            if self.cur().type == TT['KEYWORD'] and self.cur().value in ('let', 'const', 'var'):
                init = self.parse_var_decl_inline()
            else:
                init = self.parse_expr()
        self.eat(TT['SEMI'])
        test = None
        if not self.match(TT['SEMI']):
            test = self.parse_expr()
        self.eat(TT['SEMI'])
        update = None
        if not self.match(TT['RPAREN']):
            update = self.parse_expr()
        self.eat(TT['RPAREN'])
        body = self.parse_stmt()
        return node('For', init=init, test=test, update=update, body=body)

    def parse_var_decl_inline(self):
        """VarDecl without semicolon (used in for-init)"""
        kind = self.eat(TT['KEYWORD']).value
        declarations = []
        while True:
            name = self.eat(TT['IDENT']).value
            init = None
            if self.match(TT['OP'], '='):
                self.eat()
                init = self.parse_assign_expr()
            declarations.append(node('Declarator', id=name, init=init, destructure=None))
            if self.match(TT['COMMA']): self.eat()
            else: break
        return node('VarDecl', decl_kind=kind, declarations=declarations)

    def parse_while(self):
        self.eat(TT['KEYWORD'], 'while')
        self.eat(TT['LPAREN'])
        test = self.parse_expr()
        self.eat(TT['RPAREN'])
        body = self.parse_stmt()
        return node('While', test=test, body=body)

    def parse_do_while(self):
        self.eat(TT['KEYWORD'], 'do')
        body = self.parse_stmt()
        self.eat(TT['KEYWORD'], 'while')
        self.eat(TT['LPAREN'])
        test = self.parse_expr()
        self.eat(TT['RPAREN'])
        self.eat_semi()
        return node('DoWhile', body=body, test=test)

    def parse_try(self):
        self.eat(TT['KEYWORD'], 'try')
        block = self.parse_block()
        catch_param = None
        catch_body = None
        finally_body = None
        if self.match(TT['KEYWORD'], 'catch'):
            self.eat()
            if self.match(TT['LPAREN']):
                self.eat(TT['LPAREN'])
                catch_param = self.eat(TT['IDENT']).value
                self.eat(TT['RPAREN'])
            catch_body = self.parse_block()
        if self.match(TT['KEYWORD'], 'finally'):
            self.eat()
            finally_body = self.parse_block()
        return node('Try', block=block, catch_param=catch_param,
                    catch_body=catch_body, finally_body=finally_body)

    def parse_switch(self):
        self.eat(TT['KEYWORD'], 'switch')
        self.eat(TT['LPAREN'])
        discriminant = self.parse_expr()
        self.eat(TT['RPAREN'])
        self.eat(TT['LBRACE'])
        cases = []
        while not self.match(TT['RBRACE']):
            if self.match(TT['KEYWORD'], 'case'):
                self.eat()
                test = self.parse_expr()
                self.eat(TT['COLON'])
                body = []
                while not self.match(TT['KEYWORD'], 'case') and \
                      not self.match(TT['KEYWORD'], 'default') and \
                      not self.match(TT['RBRACE']):
                    body.append(self.parse_stmt())
                cases.append(node('Case', test=test, body=body))
            elif self.match(TT['KEYWORD'], 'default'):
                self.eat()
                self.eat(TT['COLON'])
                body = []
                while not self.match(TT['KEYWORD'], 'case') and \
                      not self.match(TT['KEYWORD'], 'default') and \
                      not self.match(TT['RBRACE']):
                    body.append(self.parse_stmt())
                cases.append(node('Case', test=None, body=body))
        self.eat(TT['RBRACE'])
        return node('Switch', discriminant=discriminant, cases=cases)

    def parse_class(self):
        self.eat(TT['KEYWORD'], 'class')
        name = self.eat(TT['IDENT']).value
        superclass = None
        if self.match(TT['KEYWORD'], 'extends'):
            self.eat()
            superclass = self.eat(TT['IDENT']).value
        self.eat(TT['LBRACE'])
        methods = []
        while not self.match(TT['RBRACE']):
            is_static = False
            if self.match(TT['IDENT'], 'static') or (self.cur().type == TT['KEYWORD'] and self.cur().value == 'static'):
                self.eat()
                is_static = True
            mname = self.eat(TT['IDENT']).value if self.cur().type == TT['IDENT'] else self.eat(TT['KEYWORD']).value
            params, rest_param = self.parse_params()
            body = self.parse_block()
            methods.append(node('Method', name=mname, params=params, rest_param=rest_param,
                                body=body, is_static=is_static))
        self.eat(TT['RBRACE'])
        return node('Class', name=name, superclass=superclass, methods=methods)

    # ── Expressions ──────────────────────────

    def parse_expr(self):
        return self.parse_comma_expr()

    def parse_comma_expr(self):
        left = self.parse_assign_expr()
        while self.match(TT['COMMA']):
            # Only treat comma as operator in expression context, not params
            # We don't enter here from param/arg lists since they handle commas
            # This method is only called when we need a full expression
            break
        return left

    def parse_assign_expr(self):
        left = self.parse_ternary()
        assign_ops = {'=', '+=', '-=', '*=', '/=', '%=', '**=', '&&=', '||=', '??=',
                      '<<=', '>>=', '>>>=', '&=', '|=', '^='}
        if self.cur().type == TT['OP'] and self.cur().value in assign_ops:
            op = self.eat().value
            right = self.parse_assign_expr()
            return node('Assign', op=op, left=left, right=right)
        return left

    def parse_ternary(self):
        test = self.parse_nullish()
        if self.match(TT['OP'], '?'):
            self.eat()
            consequent = self.parse_assign_expr()
            self.eat(TT['COLON'])
            alternate = self.parse_assign_expr()
            return node('Ternary', test=test, consequent=consequent, alternate=alternate)
        return test

    def parse_nullish(self):
        left = self.parse_or()
        while self.match(TT['OP'], '??'):
            op = self.eat().value
            right = self.parse_or()
            left = node('Binary', op=op, left=left, right=right)
        return left

    def parse_or(self):
        left = self.parse_and()
        while self.match(TT['OP'], '||'):
            op = self.eat().value
            right = self.parse_and()
            left = node('Logical', op=op, left=left, right=right)
        return left

    def parse_and(self):
        left = self.parse_bitwise_or()
        while self.match(TT['OP'], '&&'):
            op = self.eat().value
            right = self.parse_bitwise_or()
            left = node('Logical', op=op, left=left, right=right)
        return left

    def parse_bitwise_or(self):
        left = self.parse_bitwise_xor()
        while self.cur().type == TT['OP'] and self.cur().value == '|':
            op = self.eat().value
            right = self.parse_bitwise_xor()
            left = node('Binary', op=op, left=left, right=right)
        return left

    def parse_bitwise_xor(self):
        left = self.parse_bitwise_and()
        while self.cur().type == TT['OP'] and self.cur().value == '^':
            op = self.eat().value
            right = self.parse_bitwise_and()
            left = node('Binary', op=op, left=left, right=right)
        return left

    def parse_bitwise_and(self):
        left = self.parse_equality()
        while self.cur().type == TT['OP'] and self.cur().value == '&':
            op = self.eat().value
            right = self.parse_equality()
            left = node('Binary', op=op, left=left, right=right)
        return left

    def parse_equality(self):
        left = self.parse_relational()
        while self.cur().type == TT['OP'] and self.cur().value in ('===', '!==', '==', '!='):
            op = self.eat().value
            right = self.parse_relational()
            left = node('Binary', op=op, left=left, right=right)
        return left

    def parse_relational(self):
        left = self.parse_shift()
        rel_ops = {'<', '>', '<=', '>=', 'instanceof', 'in'}
        while True:
            if self.cur().type == TT['OP'] and self.cur().value in rel_ops:
                op = self.eat().value
            elif self.cur().type == TT['KEYWORD'] and self.cur().value in ('instanceof', 'in'):
                op = self.eat().value
            else:
                break
            right = self.parse_shift()
            left = node('Binary', op=op, left=left, right=right)
        return left

    def parse_shift(self):
        left = self.parse_additive()
        while self.cur().type == TT['OP'] and self.cur().value in ('<<', '>>', '>>>'):
            op = self.eat().value
            right = self.parse_additive()
            left = node('Binary', op=op, left=left, right=right)
        return left

    def parse_additive(self):
        left = self.parse_multiplicative()
        while self.cur().type == TT['OP'] and self.cur().value in ('+', '-'):
            op = self.eat().value
            right = self.parse_multiplicative()
            left = node('Binary', op=op, left=left, right=right)
        return left

    def parse_multiplicative(self):
        left = self.parse_exponent()
        while self.cur().type == TT['OP'] and self.cur().value in ('*', '/', '%'):
            op = self.eat().value
            right = self.parse_exponent()
            left = node('Binary', op=op, left=left, right=right)
        return left

    def parse_exponent(self):
        left = self.parse_unary()
        if self.cur().type == TT['OP'] and self.cur().value == '**':
            self.eat()
            right = self.parse_exponent()  # right associative
            return node('Binary', op='**', left=left, right=right)
        return left

    def parse_unary(self):
        if self.cur().type == TT['OP'] and self.cur().value in ('!', '-', '+', '~', '++', '--'):
            op = self.eat().value
            operand = self.parse_unary()
            return node('Unary', op=op, prefix=True, operand=operand)
        if self.cur().type == TT['KEYWORD'] and self.cur().value in ('typeof', 'void', 'delete'):
            op = self.eat().value
            operand = self.parse_unary()
            return node('Unary', op=op, prefix=True, operand=operand)
        return self.parse_postfix()

    def parse_postfix(self):
        expr = self.parse_call_member()
        if self.cur().type == TT['OP'] and self.cur().value in ('++', '--'):
            op = self.eat().value
            return node('Unary', op=op, prefix=False, operand=expr)
        return expr

    def parse_call_member(self):
        obj = self.parse_primary()
        while True:
            if self.match(TT['DOT']):
                self.eat()
                prop = self.eat(TT['IDENT']).value if self.cur().type == TT['IDENT'] else self.eat(TT['KEYWORD']).value
                obj = node('Member', obj=obj, prop=prop, computed=False)
            elif self.match(TT['LBRACKET']):
                self.eat()
                prop = self.parse_expr()
                self.eat(TT['RBRACKET'])
                obj = node('Member', obj=obj, prop=prop, computed=True)
            elif self.match(TT['LPAREN']):
                args = self.parse_args()
                obj = node('Call', callee=obj, args=args)
            elif self.cur().type == TT['OP'] and self.cur().value == '?.':
                self.eat()
                if self.match(TT['LPAREN']):
                    args = self.parse_args()
                    obj = node('OptChainCall', callee=obj, args=args)
                else:
                    prop = self.eat(TT['IDENT']).value
                    obj = node('OptChain', obj=obj, prop=prop)
            else:
                break
        return obj

    def parse_args(self):
        self.eat(TT['LPAREN'])
        args = []
        while not self.match(TT['RPAREN']):
            if self.cur().type == TT['SPREAD']:
                self.eat()
                args.append(node('Spread', expr=self.parse_assign_expr()))
            else:
                args.append(self.parse_assign_expr())
            if self.match(TT['COMMA']): self.eat()
        self.eat(TT['RPAREN'])
        return args

    def parse_primary(self):
        t = self.cur()

        if t.type == TT['NUM']:
            self.eat()
            return node('Literal', value=t.value)

        if t.type == TT['STR']:
            self.eat()
            return node('Literal', value=t.value)

        if t.type == 'TEMPLATE':
            self.eat()
            return node('Template', parts=t.value)

        if t.type == TT['BOOL']:
            self.eat()
            return node('Literal', value=t.value)

        if t.type == TT['NULL']:
            self.eat()
            return node('Literal', value=None)

        if t.type == TT['UNDEFINED']:
            self.eat()
            return node('Identifier', name='undefined')

        if t.type == TT['IDENT']:
            self.eat()
            # Arrow function: name => ...
            if self.match(TT['OP'], '=>'):
                self.eat()
                if self.match(TT['LBRACE']):
                    body = self.parse_block()
                    return node('Arrow', params=[(t.value, None)], rest_param=None, body=body, expr=False)
                else:
                    body = self.parse_assign_expr()
                    return node('Arrow', params=[(t.value, None)], rest_param=None, body=body, expr=True)
            return node('Identifier', name=t.value)

        if t.type == TT['KEYWORD'] and t.value == 'this':
            self.eat()
            return node('This')

        if t.type == TT['KEYWORD'] and t.value == 'new':
            self.eat()
            callee = self.parse_call_member_no_call()
            args = []
            if self.match(TT['LPAREN']):
                args = self.parse_args()
            return node('New', callee=callee, args=args)

        if t.type == TT['KEYWORD'] and t.value == 'function':
            self.eat()
            name = None
            if self.cur().type == TT['IDENT']:
                name = self.eat(TT['IDENT']).value
            params, rest_param = self.parse_params()
            body = self.parse_block()
            return node('FuncExpr', name=name, params=params, rest_param=rest_param, body=body)

        if t.type == TT['LPAREN']:
            self.eat()
            # Could be grouped expr or arrow params
            # Try arrow: () => or (a, b) =>
            saved = self.pos
            try:
                params, rest_param = self._try_arrow_params()
                if self.match(TT['OP'], '=>'):
                    self.eat()
                    if self.match(TT['LBRACE']):
                        body = self.parse_block()
                        return node('Arrow', params=params, rest_param=rest_param, body=body, expr=False)
                    else:
                        body = self.parse_assign_expr()
                        return node('Arrow', params=params, rest_param=rest_param, body=body, expr=True)
            except:
                pass
            self.pos = saved
            expr = self.parse_expr()
            self.eat(TT['RPAREN'])
            return node('Group', expr=expr)

        if t.type == TT['LBRACKET']:
            self.eat()
            elements = []
            while not self.match(TT['RBRACKET']):
                if self.cur().type == TT['SPREAD']:
                    self.eat()
                    elements.append(node('Spread', expr=self.parse_assign_expr()))
                elif self.match(TT['COMMA']):
                    elements.append(node('Hole'))
                    self.eat()
                    continue
                else:
                    elements.append(self.parse_assign_expr())
                if self.match(TT['COMMA']): self.eat()
            self.eat(TT['RBRACKET'])
            return node('Array', elements=elements)

        if t.type == TT['LBRACE']:
            return self.parse_object_expr()

        raise ParseError(f"Unexpected token: {t!r}")

    def _try_arrow_params(self):
        """Parse arrow function parameter list. Raises on failure."""
        params = []
        rest_param = None
        while not self.match(TT['RPAREN']):
            if self.cur().type == TT['SPREAD']:
                self.eat()
                rest_param = self.eat(TT['IDENT']).value
                break
            name = self.eat(TT['IDENT']).value
            default = None
            if self.match(TT['OP'], '='):
                self.eat()
                default = self.parse_assign_expr()
            params.append((name, default))
            if self.match(TT['COMMA']): self.eat()
        self.eat(TT['RPAREN'])
        return params, rest_param

    def parse_call_member_no_call(self):
        """Member access without call, for 'new'"""
        obj = node('Identifier', name=self.eat(TT['IDENT']).value) if self.cur().type == TT['IDENT'] else self.parse_primary()
        while self.match(TT['DOT']):
            self.eat()
            prop = self.eat(TT['IDENT']).value
            obj = node('Member', obj=obj, prop=prop, computed=False)
        return obj

    def parse_object_expr(self):
        self.eat(TT['LBRACE'])
        props = []
        while not self.match(TT['RBRACE']):
            if self.cur().type == TT['SPREAD']:
                self.eat()
                props.append(node('SpreadProp', expr=self.parse_assign_expr()))
            else:
                # key
                if self.cur().type == TT['LBRACKET']:
                    self.eat()
                    key = self.parse_assign_expr()
                    self.eat(TT['RBRACKET'])
                    computed = True
                else:
                    if self.cur().type == TT['IDENT']:
                        key_tok = self.eat(TT['IDENT'])
                    elif self.cur().type == TT['STR']:
                        key_tok = self.eat(TT['STR'])
                    elif self.cur().type == TT['NUM']:
                        key_tok = self.eat(TT['NUM'])
                    else:
                        key_tok = self.eat(TT['KEYWORD'])
                    key = node('Literal', value=key_tok.value)
                    computed = False

                # method shorthand
                if self.match(TT['LPAREN']):
                    params, rest_param = self.parse_params()
                    body = self.parse_block()
                    val = node('FuncExpr', name=None, params=params, rest_param=rest_param, body=body)
                    props.append(node('Prop', key=key, value=val, computed=computed, shorthand=False))
                elif self.match(TT['COLON']):
                    self.eat()
                    val = self.parse_assign_expr()
                    props.append(node('Prop', key=key, value=val, computed=computed, shorthand=False))
                else:
                    # shorthand {x} or {x, y}
                    props.append(node('Prop', key=key, value=key, computed=computed, shorthand=True))
            if self.match(TT['COMMA']): self.eat()
        self.eat(TT['RBRACE'])
        return node('Object', props=props)


# ─────────────────────────────────────────────
#  RUNTIME VALUES
# ─────────────────────────────────────────────

class Undefined:
    _instance = None
    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance
    def __repr__(self): return 'undefined'
    def __bool__(self): return False

UNDEFINED = Undefined()

class JSNull:
    _instance = None
    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance
    def __repr__(self): return 'null'
    def __bool__(self): return False

JS_NULL = JSNull()

class JSObject:
    def __init__(self, props=None, prototype=None):
        self.props: Dict[str, Any] = props or {}
        self.prototype = prototype

    def get(self, key):
        if key in self.props:
            return self.props[key]
        if self.prototype:
            return self.prototype.get(key)
        return UNDEFINED

    def set(self, key, val):
        self.props[str(key)] = val

    def delete(self, key):
        self.props.pop(str(key), None)

    def keys(self):
        return list(self.props.keys())

    def __repr__(self):
        inner = ', '.join(f'{k}: {js_to_display(v)}' for k, v in self.props.items())
        return '{' + inner + '}'

class JSArray(list):
    def __init__(self, items=None):
        super().__init__(items or [])
        self.props: Dict[str, Any] = {}

    def get(self, key):
        if isinstance(key, (int, float)) and not isinstance(key, bool):
            idx = int(key)
            if 0 <= idx < len(self):
                return self[idx]
            return UNDEFINED
        if isinstance(key, str):
            if key == 'length':
                return float(len(self))
            if key.lstrip('-').isdigit():
                idx = int(key)
                if 0 <= idx < len(self):
                    return self[idx]
                return UNDEFINED
            if key in self.props:
                return self.props[key]
        return UNDEFINED

    def set(self, key, val):
        if isinstance(key, (int, float)) and not isinstance(key, bool):
            idx = int(key)
            while len(self) <= idx:
                self.append(UNDEFINED)
            self[idx] = val
        elif isinstance(key, str) and key.lstrip('-').isdigit():
            idx = int(key)
            while len(self) <= idx:
                self.append(UNDEFINED)
            self[idx] = val
        else:
            self.props[str(key)] = val

    def delete(self, key):
        if isinstance(key, (int, float)):
            idx = int(key)
            if 0 <= idx < len(self):
                self[idx] = UNDEFINED
        else:
            self.props.pop(str(key), None)


class JSFunction:
    def __init__(self, name, params, rest_param, body, closure, is_expr=False, is_arrow=False, expr_body=None):
        self.name = name or 'anonymous'
        self.params = params       # list of (name, default_expr)
        self.rest_param = rest_param
        self.body = body           # AST node (Block)
        self.closure = closure     # Environment
        self.is_arrow = is_arrow
        self.expr_body = expr_body  # for arrow expr body
        self.props: Dict[str, Any] = {'prototype': JSObject()}

    def get(self, key):
        return self.props.get(key, UNDEFINED)

    def set(self, key, val):
        self.props[key] = val

    def __repr__(self):
        return f'[Function: {self.name}]'

class JSClass:
    def __init__(self, name, superclass, methods, closure):
        self.name = name
        self.superclass = superclass
        self.methods = methods
        self.closure = closure

class JSInstance(JSObject):
    def __init__(self, cls):
        super().__init__()
        self.cls = cls
        self.prototype = cls.props.get('prototype') if hasattr(cls, 'props') else None

    def get(self, key):
        if key in self.props:
            return self.props[key]
        # look up prototype chain
        cls = self.cls if isinstance(self.cls, JSClass) else None
        if cls:
            for m in cls.methods:
                if m['name'] == key and not m['is_static']:
                    def make_method(m, inst):
                        def method(*args):
                            pass
                        return m
                    return MethodRef(m, self, cls)
        return UNDEFINED

class MethodRef:
    def __init__(self, method_node, instance, cls):
        self.method_node = method_node
        self.instance = instance
        self.cls = cls

# Signals
class ReturnSignal(Exception):
    def __init__(self, value): self.value = value

class BreakSignal(Exception): pass
class ContinueSignal(Exception): pass
class ThrowSignal(Exception):
    def __init__(self, value): self.value = value


# ─────────────────────────────────────────────
#  ENVIRONMENT
# ─────────────────────────────────────────────

class Env:
    def __init__(self, parent=None):
        self.vars: Dict[str, Any] = {}
        self.parent = parent

    def get(self, name):
        if name in self.vars:
            return self.vars[name]
        if self.parent:
            return self.parent.get(name)
        return UNDEFINED

    def set(self, name, val):
        """Set in the scope where the variable is declared."""
        if name in self.vars:
            self.vars[name] = val
            return
        if self.parent:
            self.parent.set(name, val)
        else:
            self.vars[name] = val  # global fallback

    def define(self, name, val):
        self.vars[name] = val

    def assign(self, name, val):
        """Assign existing variable."""
        if name in self.vars:
            self.vars[name] = val
            return True
        if self.parent:
            return self.parent.assign(name, val)
        # global new variable
        self.vars[name] = val
        return True


# ─────────────────────────────────────────────
#  JS TYPE HELPERS
# ─────────────────────────────────────────────

def js_to_string(v) -> str:
    if isinstance(v, bool): return 'true' if v else 'false'
    if v is JS_NULL or v is None: return 'null'
    if v is UNDEFINED: return 'undefined'
    if isinstance(v, float):
        if v != v: return 'NaN'
        if v == float('inf'): return 'Infinity'
        if v == float('-inf'): return '-Infinity'
        if v == int(v) and abs(v) < 1e15: return str(int(v))
        return str(v)
    if isinstance(v, JSArray):
        return ','.join(js_to_string(x) for x in v)
    if isinstance(v, JSObject):
        return '[object Object]'
    if isinstance(v, JSFunction):
        return f'function {v.name}() {{ [native code] }}'
    return str(v)

def js_to_display(v) -> str:
    """For console.log output"""
    if v is True: return 'true'
    if v is False: return 'false'
    if v is JS_NULL or v is None: return 'null'
    if v is UNDEFINED: return 'undefined'
    if isinstance(v, float):
        if v != v: return 'NaN'
        if v == float('inf'): return 'Infinity'
        if v == float('-inf'): return '-Infinity'
        if v == int(v) and abs(v) < 1e15: return str(int(v))
        return str(v)
    if isinstance(v, JSArray):
        return '[ ' + ', '.join(js_to_display(x) for x in v) + ' ]' if v else '[]'
    if isinstance(v, JSObject):
        inner = ', '.join(f'{k}: {js_to_display(val)}' for k, val in v.props.items())
        return '{ ' + inner + ' }' if inner else '{}'
    if isinstance(v, JSFunction):
        return f'[Function: {v.name}]'
    return str(v)

def js_to_number(v) -> float:
    if isinstance(v, bool): return 1.0 if v else 0.0
    if isinstance(v, float): return v
    if v is JS_NULL or v is None: return 0.0
    if v is UNDEFINED: return float('nan')
    if isinstance(v, str):
        s = v.strip()
        if s == '': return 0.0
        try: return float(s)
        except: return float('nan')
    if isinstance(v, JSArray):
        if len(v) == 0: return 0.0
        if len(v) == 1: return js_to_number(v[0])
        return float('nan')
    return float('nan')

def js_to_bool(v) -> bool:
    if isinstance(v, bool): return v
    if v is False: return False
    if v is UNDEFINED or v is JS_NULL or v is None: return False
    if isinstance(v, float): return v != 0 and v == v
    if isinstance(v, str): return len(v) > 0
    return True  # objects, arrays, functions are truthy

def js_equal(a, b) -> bool:
    """Abstract equality (==)"""
    if type(a) == type(b) or (isinstance(a, float) and isinstance(b, float)):
        return js_strict_equal(a, b)
    # null == undefined
    if (a is JS_NULL or a is UNDEFINED) and (b is JS_NULL or b is UNDEFINED):
        return True
    # number/string coercion
    if isinstance(a, str) and isinstance(b, float):
        return js_to_number(a) == b
    if isinstance(a, float) and isinstance(b, str):
        return a == js_to_number(b)
    if isinstance(a, bool):
        return js_equal(1.0 if a else 0.0, b)
    if isinstance(b, bool):
        return js_equal(a, 1.0 if b else 0.0)
    return False

def js_strict_equal(a, b) -> bool:
    """Strict equality (===)"""
    if isinstance(a, bool) and isinstance(b, bool): return a == b
    if isinstance(a, bool) or isinstance(b, bool): return False
    if isinstance(a, float) and isinstance(b, float):
        if a != a: return False  # NaN
        return a == b
    if a is UNDEFINED and b is UNDEFINED: return True
    if (a is JS_NULL or a is None) and (b is JS_NULL or b is None): return True
    if isinstance(a, str) and isinstance(b, str): return a == b
    return a is b  # reference equality for objects/arrays


# ─────────────────────────────────────────────
#  EVALUATOR
# ─────────────────────────────────────────────

class Interpreter:
    def __init__(self):
        self.output: List[str] = []
        self.global_env = Env()
        self._setup_globals()

    def _setup_globals(self):
        env = self.global_env
        interp = self

        # console.log
        console = JSObject()
        def _log(*args):
            parts = []
            for a in args:
                parts.append(js_to_display(a))
            interp.output.append(' '.join(parts))
        console.set('log', _log)
        console.set('error', _log)
        console.set('warn', _log)
        console.set('info', _log)
        env.define('console', console)

        # Math
        math_obj = JSObject()
        math_obj.set('PI', math.pi)
        math_obj.set('E', math.e)
        math_obj.set('LN2', math.log(2))
        math_obj.set('LN10', math.log(10))
        math_obj.set('LOG2E', math.log2(math.e))
        math_obj.set('LOG10E', math.log10(math.e))
        math_obj.set('SQRT2', math.sqrt(2))
        math_obj.set('floor', lambda x: float(math.floor(js_to_number(x))))
        math_obj.set('ceil', lambda x: float(math.ceil(js_to_number(x))))
        math_obj.set('round', lambda x: float(round(js_to_number(x))))
        math_obj.set('abs', lambda x: float(abs(js_to_number(x))))
        math_obj.set('sqrt', lambda x: float(math.sqrt(js_to_number(x))))
        math_obj.set('pow', lambda x, y: float(js_to_number(x) ** js_to_number(y)))
        math_obj.set('max', lambda *args: float(max(js_to_number(a) for a in args)) if args else float('-inf'))
        math_obj.set('min', lambda *args: float(min(js_to_number(a) for a in args)) if args else float('inf'))
        math_obj.set('log', lambda x: float(math.log(js_to_number(x))))
        math_obj.set('log2', lambda x: float(math.log2(js_to_number(x))))
        math_obj.set('log10', lambda x: float(math.log10(js_to_number(x))))
        math_obj.set('sin', lambda x: float(math.sin(js_to_number(x))))
        math_obj.set('cos', lambda x: float(math.cos(js_to_number(x))))
        math_obj.set('tan', lambda x: float(math.tan(js_to_number(x))))
        math_obj.set('asin', lambda x: float(math.asin(js_to_number(x))))
        math_obj.set('acos', lambda x: float(math.acos(js_to_number(x))))
        math_obj.set('atan', lambda x: float(math.atan(js_to_number(x))))
        math_obj.set('atan2', lambda y, x: float(math.atan2(js_to_number(y), js_to_number(x))))
        math_obj.set('trunc', lambda x: float(math.trunc(js_to_number(x))))
        math_obj.set('sign', lambda x: float(1 if js_to_number(x) > 0 else (-1 if js_to_number(x) < 0 else 0)))
        math_obj.set('hypot', lambda *args: float(math.hypot(*(js_to_number(a) for a in args))))
        math_obj.set('random', lambda: __import__('random').random())
        math_obj.set('cbrt', lambda x: float(js_to_number(x) ** (1/3)))
        math_obj.set('clz32', lambda x: float(32 - len(bin(int(js_to_number(x)) & 0xffffffff).lstrip('0b')) if int(js_to_number(x)) != 0 else 32))
        env.define('Math', math_obj)

        # Date
        class JSDate(JSObject):
            def __init__(self, *args):
                super().__init__()
                if not args:
                    self._ts = time.time() * 1000
                elif len(args) == 1:
                    a = args[0]
                    if isinstance(a, float): self._ts = a
                    elif isinstance(a, str):
                        import datetime
                        try:
                            d = datetime.datetime.fromisoformat(a.replace('Z',''))
                            self._ts = d.timestamp() * 1000
                        except:
                            self._ts = float('nan')
                else:
                    import datetime
                    parts_d = [int(js_to_number(a)) for a in args]
                    while len(parts_d) < 7: parts_d.append(0)
                    d = datetime.datetime(parts_d[0], parts_d[1]+1, parts_d[2],
                                         parts_d[3], parts_d[4], parts_d[5], parts_d[6]*1000)
                    self._ts = d.timestamp() * 1000

            def get(self, key):
                import datetime
                dt = datetime.datetime.fromtimestamp(self._ts / 1000)
                methods = {
                    'getFullYear': lambda: float(dt.year),
                    'getMonth': lambda: float(dt.month - 1),
                    'getDate': lambda: float(dt.day),
                    'getDay': lambda: float(dt.weekday()),
                    'getHours': lambda: float(dt.hour),
                    'getMinutes': lambda: float(dt.minute),
                    'getSeconds': lambda: float(dt.second),
                    'getMilliseconds': lambda: float(dt.microsecond // 1000),
                    'getTime': lambda: self._ts,
                    'toISOString': lambda: dt.strftime('%Y-%m-%dT%H:%M:%S.') + f'{dt.microsecond//1000:03d}Z',
                    'toLocaleDateString': lambda: dt.strftime('%m/%d/%Y'),
                    'toLocaleString': lambda: dt.strftime('%m/%d/%Y, %I:%M:%S %p'),
                    'toString': lambda: dt.strftime('%a %b %d %Y %H:%M:%S GMT+0000'),
                    'valueOf': lambda: self._ts,
                }
                if key in methods:
                    return methods[key]
                return super().get(key)

        date_constructor = JSObject()
        date_constructor.set('now', lambda: time.time() * 1000)
        env.define('Date', date_constructor)
        env.define('_DateClass', JSDate)

        # Number
        number_obj = JSObject()
        number_obj.set('isInteger', lambda x: isinstance(x, float) and x == int(x))
        number_obj.set('isFinite', lambda x: isinstance(x, float) and x != float('inf') and x != float('-inf') and x == x)
        number_obj.set('isNaN', lambda x: isinstance(x, float) and x != x)
        number_obj.set('parseInt', lambda s, *r: interp._parse_int(s, *r))
        number_obj.set('parseFloat', lambda s: interp._parse_float(s))
        number_obj.set('MAX_VALUE', float(sys.float_info.max))
        number_obj.set('MIN_VALUE', float(sys.float_info.min))
        number_obj.set('POSITIVE_INFINITY', float('inf'))
        number_obj.set('NEGATIVE_INFINITY', float('-inf'))
        number_obj.set('NaN', float('nan'))
        number_obj.set('MAX_SAFE_INTEGER', float(2**53 - 1))
        number_obj.set('MIN_SAFE_INTEGER', float(-(2**53 - 1)))
        env.define('Number', number_obj)

        # String constructor (callable + static methods)
        def _string_constructor(x=UNDEFINED):
            if x is UNDEFINED: return ''
            return js_to_string(x)
        string_ctor = JSObject()
        string_ctor.set('fromCharCode', lambda *args: ''.join(chr(int(js_to_number(a))) for a in args))
        string_ctor.set('__call__', _string_constructor)
        env.define('String', _string_constructor)
        env.define('_StringCtor', string_ctor)

        # Array constructor
        array_obj = JSObject()
        array_obj.set('isArray', lambda x: isinstance(x, JSArray))
        array_obj.set('from', lambda x, *rest: interp._array_from(x, *rest))
        array_obj.set('of', lambda *args: JSArray(list(args)))
        env.define('Array', array_obj)

        # JSON
        json_obj = JSObject()
        json_obj.set('stringify', lambda x, *r: interp._json_stringify(x))
        json_obj.set('parse', lambda s, *r: interp._json_parse(s))
        env.define('JSON', json_obj)

        # Global functions
        env.define('parseInt', lambda s, *r: interp._parse_int(s, *r))
        env.define('parseFloat', lambda s: interp._parse_float(s))
        env.define('isNaN', lambda x: js_to_number(x) != js_to_number(x))
        env.define('isFinite', lambda x: abs(js_to_number(x)) != float('inf') and js_to_number(x) == js_to_number(x))
        env.define('NaN', float('nan'))
        env.define('Infinity', float('inf'))
        env.define('undefined', UNDEFINED)
        env.define('null', JS_NULL)

        def _typeof(v):
            if v is UNDEFINED: return 'undefined'
            if isinstance(v, bool): return 'boolean'
            if isinstance(v, float): return 'number'
            if isinstance(v, str): return 'string'
            if v is JS_NULL or v is None: return 'object'
            if isinstance(v, JSFunction) or callable(v): return 'function'
            return 'object'
        env.define('__typeof__', _typeof)

        # Number constructor (callable: Number(x) -> float)
        def _number_constructor(x=UNDEFINED):
            if x is UNDEFINED: return 0.0
            return js_to_number(x)
        number_obj.set('__call__', _number_constructor)
        env.define('Number', _number_constructor)
        env.define('_NumberObj', number_obj)

        env.define('Boolean', lambda x=UNDEFINED: False if x is UNDEFINED else js_to_bool(x))

        # Object
        obj_constructor = JSObject()
        obj_constructor.set('keys', lambda o: JSArray(list(o.props.keys()) if isinstance(o, JSObject) else (JSArray([str(i) for i in range(len(o))]) if isinstance(o, JSArray) else JSArray())))
        obj_constructor.set('values', lambda o: JSArray(list(o.props.values()) if isinstance(o, JSObject) else []))
        obj_constructor.set('entries', lambda o: JSArray([JSArray([k, v]) for k, v in o.props.items()]) if isinstance(o, JSObject) else JSArray())
        obj_constructor.set('assign', lambda target, *sources: interp._object_assign(target, *sources))
        obj_constructor.set('create', lambda proto=None, *r: JSObject(prototype=proto if isinstance(proto, JSObject) else None))
        obj_constructor.set('freeze', lambda o: o)
        obj_constructor.set('seal', lambda o: o)
        obj_constructor.set('fromEntries', lambda entries: interp._object_from_entries(entries))
        obj_constructor.set('hasOwn', lambda o, k: js_to_string(k) in o.props if isinstance(o, JSObject) else False)
        env.define('Object', obj_constructor)

        # Error constructors — store as JSObject with __error_type__ so new Error() works
        def _make_error_ctor(etype):
            ctor = JSObject()
            ctor.set('__error_type__', etype)
            ctor.set('__name__', etype)  # so new branch recognises it as class-like
            return ctor
        env.define('Error', _make_error_ctor('Error'))
        env.define('TypeError', _make_error_ctor('TypeError'))
        env.define('RangeError', _make_error_ctor('RangeError'))
        env.define('SyntaxError', _make_error_ctor('SyntaxError'))
        env.define('ReferenceError', _make_error_ctor('ReferenceError'))

    def _make_error(self, msg='', name='Error'):
        e = JSObject()
        e.set('message', js_to_string(msg))
        e.set('name', name)
        return e

    def _parse_int(self, s, radix=None):
        s = js_to_string(s).strip()
        base = int(js_to_number(radix)) if radix and radix is not UNDEFINED else 10
        if s.startswith('0x') or s.startswith('0X'):
            base = 16
            s = s[2:]
        try:
            # collect valid chars
            valid = ''
            for c in s:
                try:
                    int(c, base)
                    valid += c
                except:
                    break
            return float(int(valid, base)) if valid else float('nan')
        except:
            return float('nan')

    def _parse_float(self, s):
        s = js_to_string(s).strip()
        # collect valid float chars
        m = re.match(r'^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?', s)
        if m:
            try: return float(m.group(0))
            except: pass
        return float('nan')

    def _array_from(self, x, *rest):
        mapfn = rest[0] if rest else None
        if isinstance(x, JSArray):
            result = JSArray(list(x))
        elif isinstance(x, str):
            result = JSArray(list(x))
        elif isinstance(x, JSObject):
            length = js_to_number(x.get('length'))
            result = JSArray([x.get(str(i)) for i in range(int(length))])
        else:
            result = JSArray()
        if mapfn and callable(mapfn):
            result = JSArray([self._call(mapfn, [v, float(i)]) for i, v in enumerate(result)])
        return result

    def _object_assign(self, target, *sources):
        if not isinstance(target, JSObject): return target
        for src in sources:
            if isinstance(src, JSObject):
                for k, v in src.props.items():
                    target.set(k, v)
        return target

    def _object_from_entries(self, entries):
        result = JSObject()
        if isinstance(entries, JSArray):
            for entry in entries:
                if isinstance(entry, JSArray) and len(entry) >= 2:
                    result.set(js_to_string(entry[0]), entry[1])
        return result

    def _json_stringify(self, v, indent=None):
        def convert(x):
            if x is UNDEFINED or callable(x): return None
            if x is JS_NULL or x is None: return None
            if isinstance(x, bool): return x
            if isinstance(x, float):
                if x != x or x == float('inf') or x == float('-inf'): return None
                return int(x) if x == int(x) else x
            if isinstance(x, str): return x
            if isinstance(x, JSArray): return [convert(i) for i in x]
            if isinstance(x, JSObject):
                return {k: convert(v) for k, v in x.props.items() if not callable(v)}
            return str(x)
        import json
        return json.dumps(convert(v), separators=(',', ':'))

    def _json_parse(self, s):
        import json
        def convert(x):
            if x is None: return JS_NULL
            if isinstance(x, bool): return x
            if isinstance(x, (int, float)): return float(x)
            if isinstance(x, str): return x
            if isinstance(x, list): return JSArray([convert(i) for i in x])
            if isinstance(x, dict):
                o = JSObject()
                for k, v in x.items(): o.set(k, convert(v))
                return o
        try: return convert(json.loads(js_to_string(s)))
        except: raise ThrowSignal(self._make_error('JSON parse error', 'SyntaxError'))

    # ── Eval ─────────────────────────────────

    def run(self, ast):
        # First pass: hoist function declarations
        self._hoist(ast, self.global_env)
        self._exec(ast, self.global_env)

    def _hoist(self, node, env):
        if node['kind'] == 'Program':
            for s in node['body']:
                self._hoist(s, env)
        elif node['kind'] == 'FuncDecl':
            fn = JSFunction(
                node['name'], node['params'], node['rest_param'],
                node['body'], env
            )
            env.define(node['name'], fn)
        elif node['kind'] == 'Block':
            for s in node['body']:
                if s['kind'] == 'FuncDecl':
                    self._hoist(s, env)

    def _exec(self, node, env):
        k = node['kind']

        if k == 'Program':
            for s in node['body']:
                self._exec(s, env)

        elif k == 'Block':
            block_env = Env(env)
            for s in node['body']:
                self._exec(s, block_env)

        elif k == 'Empty':
            pass

        elif k == 'ExprStmt':
            self._eval(node['expr'], env)

        elif k == 'VarDecl':
            for d in node['declarations']:
                val = self._eval(d['init'], env) if d['init'] else UNDEFINED
                if d['destructure'] == 'array':
                    self._destructure_array(d['id'], val, env)
                elif d['destructure'] == 'object':
                    self._destructure_object(d['id'], val, env)
                else:
                    env.define(d['id'], val)

        elif k == 'FuncDecl':
            pass  # already hoisted

        elif k == 'Return':
            val = self._eval(node['value'], env) if node['value'] else UNDEFINED
            raise ReturnSignal(val)

        elif k == 'If':
            if js_to_bool(self._eval(node['test'], env)):
                self._exec(node['consequent'], env)
            elif node['alternate']:
                self._exec(node['alternate'], env)

        elif k == 'For':
            loop_env = Env(env)
            if node['init']:
                if node['init']['kind'] == 'VarDecl':
                    self._exec(node['init'], loop_env)
                else:
                    self._eval(node['init'], loop_env)
            while True:
                if node['test'] and not js_to_bool(self._eval(node['test'], loop_env)):
                    break
                try:
                    iter_env = Env(loop_env)
                    self._exec(node['body'], iter_env)
                except BreakSignal:
                    break
                except ContinueSignal:
                    pass
                if node['update']:
                    self._eval(node['update'], loop_env)

        elif k == 'ForOf':
            iterable = self._eval(node['iterable'], env)
            items = list(iterable) if isinstance(iterable, JSArray) else (
                list(iterable) if isinstance(iterable, str) else []
            )
            for item in items:
                loop_env = Env(env)
                loop_env.define(node['var'], item)
                try:
                    self._exec(node['body'], loop_env)
                except BreakSignal:
                    break
                except ContinueSignal:
                    continue

        elif k == 'ForIn':
            obj = self._eval(node['obj'], env)
            keys = []
            if isinstance(obj, JSObject):
                keys = obj.keys()
            elif isinstance(obj, JSArray):
                keys = [str(i) for i in range(len(obj))]
            for key in keys:
                loop_env = Env(env)
                loop_env.define(node['var'], key)
                try:
                    self._exec(node['body'], loop_env)
                except BreakSignal:
                    break
                except ContinueSignal:
                    continue

        elif k == 'While':
            while js_to_bool(self._eval(node['test'], env)):
                try:
                    iter_env = Env(env)
                    self._exec(node['body'], iter_env)
                except BreakSignal:
                    break
                except ContinueSignal:
                    continue

        elif k == 'DoWhile':
            while True:
                try:
                    iter_env = Env(env)
                    self._exec(node['body'], iter_env)
                except BreakSignal:
                    break
                except ContinueSignal:
                    pass
                if not js_to_bool(self._eval(node['test'], env)):
                    break

        elif k == 'Break':
            raise BreakSignal()

        elif k == 'Continue':
            raise ContinueSignal()

        elif k == 'Throw':
            raise ThrowSignal(self._eval(node['expr'], env))

        elif k == 'Try':
            try:
                try_env = Env(env)
                self._exec(node['block'], try_env)
            except ThrowSignal as e:
                if node['catch_body']:
                    catch_env = Env(env)
                    if node['catch_param']:
                        catch_env.define(node['catch_param'], e.value)
                    self._exec(node['catch_body'], catch_env)
            finally:
                if node['finally_body']:
                    self._exec(node['finally_body'], Env(env))

        elif k == 'Switch':
            val = self._eval(node['discriminant'], env)
            fell_through = False
            broken = False
            for case in node['cases']:
                if not fell_through:
                    if case['test'] is None:  # default
                        fell_through = True
                    elif js_strict_equal(val, self._eval(case['test'], env)):
                        fell_through = True
                if fell_through:
                    try:
                        for s in case['body']:
                            self._exec(s, env)
                    except BreakSignal:
                        broken = True
                        break
                if broken: break

        elif k == 'Class':
            cls = self._create_class(node, env)
            env.define(node['name'], cls)

        else:
            # treat as expression
            self._eval(node, env)

    def _destructure_array(self, pattern, val, env):
        arr = val if isinstance(val, JSArray) else JSArray()
        for i, name in enumerate(pattern):
            if name is None: continue
            if isinstance(name, tuple) and name[0] == 'rest':
                env.define(name[1], JSArray(list(arr[i:])))
                break
            env.define(name, arr[i] if i < len(arr) else UNDEFINED)

    def _destructure_object(self, pattern, val, env):
        obj = val if isinstance(val, JSObject) else JSObject()
        for key, alias in pattern:
            env.define(alias, obj.get(key))

    def _create_class(self, node, env):
        cls = JSObject()
        cls.set('__name__', node['name'])
        cls.set('__methods__', node['methods'])
        cls.set('__superclass__', node.get('superclass'))
        cls.set('__closure__', env)
        cls.set('prototype', JSObject())
        return cls

    # ── Expression evaluator ─────────────────

    def _eval(self, node, env) -> Any:
        if node is None:
            return UNDEFINED
        k = node['kind']

        if k == 'Literal':
            v = node['value']
            if v is None: return JS_NULL
            return v

        if k == 'Identifier':
            return env.get(node['name'])

        if k == 'Template':
            result = ''
            for part_type, part_val in node['parts']:
                if part_type == 'str':
                    result += part_val
                else:
                    tokens = tokenize(part_val)
                    parser = Parser(tokens)
                    expr_ast = parser.parse_assign_expr()
                    result += js_to_string(self._eval(expr_ast, env))
            return result

        if k == 'This':
            return env.get('this') or JS_NULL

        if k == 'Group':
            return self._eval(node['expr'], env)

        if k == 'Array':
            items = []
            for el in node['elements']:
                if el['kind'] == 'Spread':
                    spread_val = self._eval(el['expr'], env)
                    if isinstance(spread_val, JSArray):
                        items.extend(list(spread_val))
                    elif isinstance(spread_val, str):
                        items.extend(list(spread_val))
                elif el['kind'] == 'Hole':
                    items.append(UNDEFINED)
                else:
                    items.append(self._eval(el, env))
            return JSArray(items)

        if k == 'Object':
            obj = JSObject()
            for prop in node['props']:
                if prop['kind'] == 'SpreadProp':
                    src = self._eval(prop['expr'], env)
                    if isinstance(src, JSObject):
                        for kk, vv in src.props.items():
                            obj.set(kk, vv)
                else:
                    if prop['computed']:
                        key = js_to_string(self._eval(prop['key'], env))
                    else:
                        key = js_to_string(prop['key']['value'])

                    if prop['shorthand']:
                        val = env.get(key)
                    else:
                        val = self._eval(prop['value'], env)
                    obj.set(key, val)
            return obj

        if k == 'FuncExpr':
            return JSFunction(
                node['name'], node['params'], node['rest_param'],
                node['body'], env
            )

        if k == 'Arrow':
            fn = JSFunction(
                'arrow', node['params'], node['rest_param'],
                node['body'], env, is_arrow=True
            )
            fn.expr_body = node.get('expr', False)
            return fn

        if k == 'Unary':
            return self._eval_unary(node, env)

        if k == 'Binary':
            return self._eval_binary(node, env)

        if k == 'Logical':
            return self._eval_logical(node, env)

        if k == 'Assign':
            return self._eval_assign(node, env)

        if k == 'Ternary':
            test = js_to_bool(self._eval(node['test'], env))
            return self._eval(node['consequent'] if test else node['alternate'], env)

        if k == 'Member':
            obj = self._eval(node['obj'], env)
            if node['computed']:
                prop = self._eval(node['prop'], env)
            else:
                prop = node['prop']
            return self._get_prop(obj, prop)

        if k == 'OptChain':
            obj = self._eval(node['obj'], env)
            if obj is UNDEFINED or obj is JS_NULL or obj is None:
                return UNDEFINED
            return self._get_prop(obj, node['prop'])

        if k == 'Call':
            return self._eval_call(node, env)

        if k == 'OptChainCall':
            callee = self._eval(node['callee'], env)
            if callee is UNDEFINED or callee is JS_NULL or callee is None:
                return UNDEFINED
            args = [self._eval_arg(a, env) for a in node['args']]
            return self._call(callee, args)

        if k == 'New':
            return self._eval_new(node, env)

        if k == 'Spread':
            return self._eval(node['expr'], env)

        return UNDEFINED

    def _eval_arg(self, arg_node, env):
        if arg_node['kind'] == 'Spread':
            val = self._eval(arg_node['expr'], env)
            return ('spread', val)
        return self._eval(arg_node, env)

    def _eval_unary(self, node, env):
        op = node['op']
        prefix = node['prefix']

        if op == 'typeof':
            operand = node['operand']
            if operand['kind'] == 'Identifier':
                v = env.get(operand['name'])
            else:
                v = self._eval(operand, env)
            if v is UNDEFINED: return 'undefined'
            if isinstance(v, bool): return 'boolean'
            if isinstance(v, float): return 'number'
            if isinstance(v, str): return 'string'
            if v is JS_NULL or v is None: return 'object'
            if isinstance(v, JSFunction) or callable(v): return 'function'
            return 'object'

        if op == 'void':
            self._eval(node['operand'], env)
            return UNDEFINED

        if op == 'delete':
            operand = node['operand']
            if operand['kind'] == 'Member':
                obj = self._eval(operand['obj'], env)
                prop = self._eval(operand['prop'], env) if operand['computed'] else operand['prop']
                if isinstance(obj, (JSObject, JSArray)):
                    obj.delete(prop)
            return True

        if op == '!' and prefix:
            return not js_to_bool(self._eval(node['operand'], env))

        if op == '-' and prefix:
            return -js_to_number(self._eval(node['operand'], env))

        if op == '+' and prefix:
            return js_to_number(self._eval(node['operand'], env))

        if op == '~' and prefix:
            return float(~int(js_to_number(self._eval(node['operand'], env))))

        if op == '++':
            operand = node['operand']
            old = js_to_number(self._eval(operand, env))
            new_val = old + 1
            self._assign_lval(operand, new_val, env)
            return old if not prefix else new_val

        if op == '--':
            operand = node['operand']
            old = js_to_number(self._eval(operand, env))
            new_val = old - 1
            self._assign_lval(operand, new_val, env)
            return old if not prefix else new_val

        return UNDEFINED

    def _eval_binary(self, node, env):
        op = node['op']
        left = self._eval(node['left'], env)

        # short-circuit for some ops would go here, but we evaluate both sides for binary
        right = self._eval(node['right'], env)

        if op == '+':
            if isinstance(left, str) or isinstance(right, str):
                return js_to_string(left) + js_to_string(right)
            ln = js_to_number(left)
            rn = js_to_number(right)
            return ln + rn

        if op == '-': return js_to_number(left) - js_to_number(right)
        if op == '*': return js_to_number(left) * js_to_number(right)
        if op == '/':
            r = js_to_number(right)
            l = js_to_number(left)
            if r == 0:
                if l == 0: return float('nan')
                return float('inf') if l > 0 else float('-inf')
            return l / r
        if op == '%':
            r = js_to_number(right)
            l = js_to_number(left)
            if r == 0: return float('nan')
            return math.fmod(l, r)
        if op == '**': return js_to_number(left) ** js_to_number(right)

        if op == '===': return js_strict_equal(left, right)
        if op == '!==': return not js_strict_equal(left, right)
        if op == '==': return js_equal(left, right)
        if op == '!=': return not js_equal(left, right)

        if op == '<':
            if isinstance(left, str) and isinstance(right, str):
                return left < right
            return js_to_number(left) < js_to_number(right)
        if op == '>':
            if isinstance(left, str) and isinstance(right, str):
                return left > right
            return js_to_number(left) > js_to_number(right)
        if op == '<=':
            if isinstance(left, str) and isinstance(right, str):
                return left <= right
            return js_to_number(left) <= js_to_number(right)
        if op == '>=':
            if isinstance(left, str) and isinstance(right, str):
                return left >= right
            return js_to_number(left) >= js_to_number(right)

        if op == '&': return float(int(js_to_number(left)) & int(js_to_number(right)))
        if op == '|': return float(int(js_to_number(left)) | int(js_to_number(right)))
        if op == '^': return float(int(js_to_number(left)) ^ int(js_to_number(right)))
        if op == '<<': return float(int(js_to_number(left)) << (int(js_to_number(right)) & 31))
        if op == '>>': return float(int(js_to_number(left)) >> (int(js_to_number(right)) & 31))
        if op == '>>>':
            l = int(js_to_number(left)) & 0xffffffff
            r = int(js_to_number(right)) & 31
            return float(l >> r)

        if op == '??':
            return right if (left is UNDEFINED or left is JS_NULL or left is None) else left

        if op == 'instanceof':
            if isinstance(right, JSObject) and right.get('__name__') is not UNDEFINED:
                if isinstance(left, JSObject) and left.get('__class__') is right:
                    return True
            return False

        if op == 'in':
            if isinstance(right, JSObject):
                return js_to_string(left) in right.props
            if isinstance(right, JSArray):
                return js_to_string(left).isdigit() and int(js_to_string(left)) < len(right)
            return False

        return UNDEFINED

    def _eval_logical(self, node, env):
        op = node['op']
        left = self._eval(node['left'], env)
        if op == '&&':
            return left if not js_to_bool(left) else self._eval(node['right'], env)
        if op == '||':
            return left if js_to_bool(left) else self._eval(node['right'], env)
        if op == '??':
            return left if (left is not UNDEFINED and left is not JS_NULL and left is not None) else self._eval(node['right'], env)
        return UNDEFINED

    def _eval_assign(self, node, env):
        op = node['op']
        if op == '=':
            val = self._eval(node['right'], env)
            self._assign_lval(node['left'], val, env)
            return val

        current = self._eval(node['left'], env)
        right = self._eval(node['right'], env)

        ops = {
            '+=': lambda a, b: (js_to_string(a) + js_to_string(b)) if isinstance(a, str) or isinstance(b, str) else js_to_number(a) + js_to_number(b),
            '-=': lambda a, b: js_to_number(a) - js_to_number(b),
            '*=': lambda a, b: js_to_number(a) * js_to_number(b),
            '/=': lambda a, b: js_to_number(a) / js_to_number(b) if js_to_number(b) != 0 else (float('inf') if js_to_number(a) >= 0 else float('-inf')),
            '%=': lambda a, b: math.fmod(js_to_number(a), js_to_number(b)) if js_to_number(b) != 0 else float('nan'),
            '**=': lambda a, b: js_to_number(a) ** js_to_number(b),
            '&&=': lambda a, b: b if js_to_bool(a) else a,
            '||=': lambda a, b: a if js_to_bool(a) else b,
            '??=': lambda a, b: a if (a is not UNDEFINED and a is not JS_NULL) else b,
            '<<=': lambda a, b: float(int(js_to_number(a)) << (int(js_to_number(b)) & 31)),
            '>>=': lambda a, b: float(int(js_to_number(a)) >> (int(js_to_number(b)) & 31)),
            '>>>=': lambda a, b: float((int(js_to_number(a)) & 0xffffffff) >> (int(js_to_number(b)) & 31)),
            '&=': lambda a, b: float(int(js_to_number(a)) & int(js_to_number(b))),
            '|=': lambda a, b: float(int(js_to_number(a)) | int(js_to_number(b))),
            '^=': lambda a, b: float(int(js_to_number(a)) ^ int(js_to_number(b))),
        }
        val = ops.get(op, lambda a, b: a)(current, right)
        self._assign_lval(node['left'], val, env)
        return val

    def _assign_lval(self, lval_node, val, env):
        k = lval_node['kind']
        if k == 'Identifier':
            env.assign(lval_node['name'], val)
        elif k == 'Member':
            obj = self._eval(lval_node['obj'], env)
            if lval_node['computed']:
                prop = self._eval(lval_node['prop'], env)
            else:
                prop = lval_node['prop']
            if isinstance(obj, (JSObject, JSArray)):
                obj.set(prop if isinstance(prop, str) else js_to_number(prop), val)
            elif isinstance(obj, JSFunction):
                obj.set(js_to_string(prop), val)

    def _eval_call(self, node, env):
        callee_node = node['callee']

        # Collect args (handling spread)
        raw_args = []
        for a in node['args']:
            if a['kind'] == 'Spread':
                spread_val = self._eval(a['expr'], env)
                if isinstance(spread_val, JSArray):
                    raw_args.extend(list(spread_val))
                else:
                    raw_args.append(spread_val)
            else:
                raw_args.append(self._eval(a, env))

        # Method call: obj.method(...)
        if callee_node['kind'] == 'Member':
            obj = self._eval(callee_node['obj'], env)
            prop = callee_node['prop'] if not callee_node['computed'] else js_to_string(self._eval(callee_node['prop'], env))
            method = self._get_prop(obj, prop)
            return self._call_method(method, obj, raw_args)

        callee = self._eval(callee_node, env)
        return self._call(callee, raw_args)

    def _eval_new(self, node, env):
        callee = self._eval(node['callee'], env)
        args = [self._eval(a, env) for a in node['args']]

        # Error constructors: Error, TypeError, RangeError, etc.
        if isinstance(callee, JSObject) and callee.get('__error_type__') is not UNDEFINED:
            etype = callee.get('__error_type__')
            msg = args[0] if args else ''
            return self._make_error(msg, etype)

        # Check if it's a user-defined class object
        if isinstance(callee, JSObject) and callee.get('__name__') is not UNDEFINED:
            instance = JSObject()
            instance.set('__class__', callee)
            closure = callee.get('__closure__')
            methods = callee.get('__methods__')
            if isinstance(methods, list):
                for m in methods:
                    if m['name'] == 'constructor':
                        self._call_user_func(
                            JSFunction(None, m['params'], m['rest_param'], m['body'], closure),
                            args, this=instance
                        )
                        break
            return instance

        # Native function used as constructor (Date, etc.)
        if isinstance(callee, JSObject) and callee.get('__name__') is UNDEFINED:
            date_class = env.get('_DateClass')
            if callee is env.get('Date') and date_class is not UNDEFINED:
                return date_class(*args)
            instance = JSObject()
            return instance

        if isinstance(callee, JSFunction):
            instance = JSObject()
            proto = callee.get('prototype')
            if isinstance(proto, JSObject):
                instance.prototype = proto
            try:
                result = self._call_user_func(callee, args, this=instance)
                if isinstance(result, JSObject):
                    return result
            except ReturnSignal as r:
                if isinstance(r.value, JSObject):
                    return r.value
            return instance

        # Callable native constructor (Number, String, Boolean)
        if callable(callee):
            try:
                result = callee(*args)
                if isinstance(result, JSObject):
                    return result
                # Wrap primitive in object shell
                wrapper = JSObject()
                wrapper.set('__value__', result)
                return wrapper
            except Exception:
                pass

        return JSObject()

    def _call(self, fn, args):
        if callable(fn) and not isinstance(fn, JSFunction):
            result = fn(*args)
            return UNDEFINED if result is None else result
        if isinstance(fn, JSFunction):
            return self._call_user_func(fn, args)
        if isinstance(fn, MethodRef):
            return self._call_method_ref(fn, args)
        raise ThrowSignal(self._make_error(f'{js_to_string(fn)} is not a function', 'TypeError'))

    def _call_method(self, method, this_val, args):
        if callable(method) and not isinstance(method, JSFunction):
            result = method(*args)
            return UNDEFINED if result is None else result
        if isinstance(method, JSFunction):
            return self._call_user_func(method, args, this=this_val)
        if isinstance(method, MethodRef):
            return self._call_method_ref(method, args)
        raise ThrowSignal(self._make_error(f'{js_to_string(method)} is not a function', 'TypeError'))

    def _call_method_ref(self, mref, args):
        m = mref.method_node
        closure = mref.cls.get('__closure__') if isinstance(mref.cls, JSObject) else mref.cls.closure
        fn = JSFunction(m['name'], m['params'], m.get('rest_param'), m['body'], closure)
        return self._call_user_func(fn, args, this=mref.instance)

    def _call_user_func(self, fn: JSFunction, args: list, this=None):
        call_env = Env(fn.closure)

        # Bind 'this'
        if fn.is_arrow:
            call_env.define('this', fn.closure.get('this') if fn.closure else UNDEFINED)
        else:
            call_env.define('this', this if this is not None else UNDEFINED)

        # Bind params
        arg_idx = 0
        for param_name, default_expr in fn.params:
            if arg_idx < len(args) and args[arg_idx] is not UNDEFINED:
                call_env.define(param_name, args[arg_idx])
            elif default_expr is not None:
                call_env.define(param_name, self._eval(default_expr, call_env))
            else:
                call_env.define(param_name, UNDEFINED)
            arg_idx += 1

        if fn.rest_param:
            call_env.define(fn.rest_param, JSArray(args[arg_idx:]))

        # arguments object
        call_env.define('arguments', JSArray(args))

        # Execute body
        if fn.expr_body:
            return self._eval(fn.body, call_env)

        try:
            self._hoist(fn.body, call_env)
            self._exec(fn.body, call_env)
            return UNDEFINED
        except ReturnSignal as r:
            return r.value

    # ── Property access & methods ─────────────

    def _get_prop(self, obj, prop):
        prop_str = js_to_string(prop) if not isinstance(prop, str) else prop

        # Number methods
        if isinstance(obj, float):
            if prop_str == 'toFixed':
                return lambda digits=0: format(obj, f'.{int(js_to_number(digits))}f')
            if prop_str == 'toString':
                return lambda radix=10: format(int(obj), 'x' if radix == 16 else 'o' if radix == 8 else 'b' if radix == 2 else 'd') if isinstance(radix, float) else js_to_string(obj)
            if prop_str == 'toLocaleString':
                return lambda: js_to_string(obj)
            if prop_str == 'toPrecision':
                return lambda p: format(obj, f'.{int(js_to_number(p))}g')
            if prop_str == 'valueOf':
                return lambda: obj
            return UNDEFINED

        # Boolean methods
        if isinstance(obj, bool):
            if prop_str == 'toString': return lambda: 'true' if obj else 'false'
            return UNDEFINED

        # String methods
        if isinstance(obj, str):
            return self._string_method(obj, prop_str)

        # Array methods
        if isinstance(obj, JSArray):
            return self._array_method(obj, prop_str)

        # JSObject / JSFunction
        if isinstance(obj, (JSObject, JSFunction)):
            v = obj.get(prop_str)
            if v is not UNDEFINED:
                return v
            # prototype chain for JSInstance
            if isinstance(obj, JSObject) and obj.prototype:
                v = obj.prototype.get(prop_str)
                if v is not UNDEFINED:
                    return v
            # Check class methods
            cls = obj.get('__class__') if isinstance(obj, JSObject) else None
            if isinstance(cls, JSObject):
                methods = cls.get('__methods__')
                if isinstance(methods, list):
                    for m in methods:
                        if m['name'] == prop_str and not m['is_static']:
                            return MethodRef(m, obj, cls)
            return UNDEFINED

        if obj is JS_NULL or obj is UNDEFINED or obj is None:
            raise ThrowSignal(self._make_error(
                f"Cannot read properties of {js_to_string(obj)} (reading '{prop_str}')", 'TypeError'
            ))

        return UNDEFINED

    def _string_method(self, s: str, prop: str):
        if prop == 'length': return float(len(s))
        if prop == 'charAt': return lambda i=0: s[int(js_to_number(i))] if 0 <= int(js_to_number(i)) < len(s) else ''
        if prop == 'charCodeAt': return lambda i=0: float(ord(s[int(js_to_number(i))])) if 0 <= int(js_to_number(i)) < len(s) else float('nan')
        if prop == 'at': return lambda i: s[int(js_to_number(i))] if -len(s) <= int(js_to_number(i)) < len(s) else UNDEFINED
        if prop == 'toUpperCase': return lambda: s.upper()
        if prop == 'toLowerCase': return lambda: s.lower()
        if prop == 'trim': return lambda: s.strip()
        if prop == 'trimStart' or prop == 'trimLeft': return lambda: s.lstrip()
        if prop == 'trimEnd' or prop == 'trimRight': return lambda: s.rstrip()
        if prop == 'split':
            def _split(sep=UNDEFINED, limit=UNDEFINED):
                if sep is UNDEFINED: return JSArray([s])
                sep_s = js_to_string(sep) if sep is not UNDEFINED else ''
                result = s.split(sep_s) if sep_s != '' else list(s)
                if limit is not UNDEFINED:
                    lim = int(js_to_number(limit))
                    result = result[:lim]
                return JSArray(result)
            return _split
        if prop == 'slice':
            def _slice(start=UNDEFINED, end=UNDEFINED):
                n = len(s)
                st = int(js_to_number(start)) if start is not UNDEFINED else 0
                en = int(js_to_number(end)) if end is not UNDEFINED else n
                st = max(0, n + st if st < 0 else st)
                en = max(0, n + en if en < 0 else min(en, n))
                return s[st:en]
            return _slice
        if prop == 'substring':
            def _substring(start=0, end=UNDEFINED):
                st = max(0, int(js_to_number(start)))
                en = len(s) if end is UNDEFINED else max(0, int(js_to_number(end)))
                if st > en: st, en = en, st
                return s[st:en]
            return _substring
        if prop == 'substr':
            def _substr(start=0, length=UNDEFINED):
                st = int(js_to_number(start))
                if st < 0: st = max(0, len(s) + st)
                ln = len(s) - st if length is UNDEFINED else int(js_to_number(length))
                return s[st:st+ln]
            return _substr
        if prop == 'indexOf': return lambda sub, *pos: float(s.find(js_to_string(sub), int(js_to_number(pos[0])) if pos else 0))
        if prop == 'lastIndexOf': return lambda sub, *pos: float(s.rfind(js_to_string(sub)))
        if prop == 'includes': return lambda sub, *pos: js_to_string(sub) in s
        if prop == 'startsWith': return lambda pre, *pos: s.startswith(js_to_string(pre))
        if prop == 'endsWith': return lambda suf, *pos: s.endswith(js_to_string(suf))
        if prop == 'replace':
            def _replace(pattern, replacement):
                p = js_to_string(pattern) if not isinstance(pattern, JSObject) else None
                if p is not None:
                    r = js_to_string(replacement) if not callable(replacement) else None
                    if r is not None:
                        return s.replace(p, r, 1)
                    else:
                        idx = s.find(p)
                        if idx == -1: return s
                        match_str = p
                        repl = js_to_string(self._call(replacement, [match_str, float(idx), s]))
                        return s[:idx] + repl + s[idx+len(p):]
                return s
            return _replace
        if prop == 'replaceAll':
            def _replaceall(pattern, replacement):
                p = js_to_string(pattern)
                r = js_to_string(replacement) if not callable(replacement) else None
                if r is not None:
                    return s.replace(p, r)
                else:
                    parts = s.split(p)
                    result = parts[0]
                    for part in parts[1:]:
                        repl = js_to_string(self._call(replacement, [p, float(s.find(p)), s]))
                        result += repl + part
                    return result
            return _replaceall
        if prop == 'match':
            def _match(pattern):
                if isinstance(pattern, JSObject) and pattern.get('__regex__') is not UNDEFINED:
                    import re as _re
                    rx = pattern.get('__regex__')
                    flags = pattern.get('__flags__') or ''
                    fl = 0
                    if 'i' in flags: fl |= _re.IGNORECASE
                    if 'm' in flags: fl |= _re.MULTILINE
                    if 'g' in flags:
                        matches = _re.findall(rx, s, fl)
                        return JSArray(matches) if matches else JS_NULL
                    m = _re.search(rx, s, fl)
                    if not m: return JS_NULL
                    return JSArray([m.group(0)] + list(m.groups()))
                p = js_to_string(pattern)
                idx = s.find(p)
                if idx == -1: return JS_NULL
                return JSArray([p])
            return _match
        if prop == 'search':
            def _search(pattern):
                if isinstance(pattern, JSObject) and pattern.get('__regex__') is not UNDEFINED:
                    import re as _re
                    rx = pattern.get('__regex__')
                    flags = pattern.get('__flags__') or ''
                    fl = _re.IGNORECASE if 'i' in flags else 0
                    m = _re.search(rx, s, fl)
                    return float(m.start()) if m else -1.0
                return float(s.find(js_to_string(pattern)))
            return _search
        if prop == 'concat': return lambda *args: s + ''.join(js_to_string(a) for a in args)
        if prop == 'padStart':
            def _padStart(length, pad=' '):
                ln = int(js_to_number(length))
                return js_to_string(pad) * max(0, (ln - len(s)) // len(js_to_string(pad)) + 1) + s if len(s) < ln else s
            return _padStart
        if prop == 'padEnd':
            def _padEnd(length, pad=' '):
                ln = int(js_to_number(length))
                pad_s = js_to_string(pad)
                extra = max(0, ln - len(s))
                return s + (pad_s * (extra // len(pad_s) + 1))[:extra]
            return _padEnd
        if prop == 'repeat': return lambda n: s * int(js_to_number(n))
        if prop == 'toString': return lambda: s
        if prop == 'valueOf': return lambda: s
        if prop == 'codePointAt': return lambda i=0: float(ord(s[int(js_to_number(i))])) if int(js_to_number(i)) < len(s) else UNDEFINED
        if prop == 'normalize': return lambda *args: s
        if prop == 'localeCompare': return lambda other: float((s > js_to_string(other)) - (s < js_to_string(other)))
        # index access
        try:
            idx = int(prop)
            return s[idx] if 0 <= idx < len(s) else UNDEFINED
        except:
            pass
        return UNDEFINED

    def _array_method(self, arr: JSArray, prop: str):
        if prop == 'length': return float(len(arr))

        if prop == 'push':
            def _push(*items):
                arr.extend(items)
                return float(len(arr))
            return _push

        if prop == 'pop':
            return lambda: arr.pop() if arr else UNDEFINED

        if prop == 'shift':
            return lambda: arr.pop(0) if arr else UNDEFINED

        if prop == 'unshift':
            def _unshift(*items):
                for i, item in enumerate(items):
                    arr.insert(i, item)
                return float(len(arr))
            return _unshift

        if prop == 'reverse':
            def _reverse():
                arr.reverse()
                return arr
            return _reverse

        if prop == 'sort':
            def _sort(comparefn=UNDEFINED):
                if comparefn is UNDEFINED or comparefn is None:
                    arr.sort(key=lambda x: js_to_string(x))
                else:
                    import functools
                    def cmp(a, b):
                        r = self._call(comparefn, [a, b])
                        n = js_to_number(r)
                        return -1 if n < 0 else (1 if n > 0 else 0)
                    arr.sort(key=functools.cmp_to_key(cmp))
                return arr
            return _sort

        if prop == 'slice':
            def _slice(start=UNDEFINED, end=UNDEFINED):
                n = len(arr)
                st = 0 if start is UNDEFINED else int(js_to_number(start))
                en = n if end is UNDEFINED else int(js_to_number(end))
                st = max(0, n + st if st < 0 else st)
                en = max(0, n + en if en < 0 else min(en, n))
                return JSArray(arr[st:en])
            return _slice

        if prop == 'splice':
            def _splice(start, deleteCount=UNDEFINED, *items):
                st = int(js_to_number(start))
                n = len(arr)
                if st < 0: st = max(0, n + st)
                if deleteCount is UNDEFINED:
                    dc = n - st
                else:
                    dc = max(0, int(js_to_number(deleteCount)))
                removed = JSArray(arr[st:st+dc])
                arr[st:st+dc] = list(items)
                return removed
            return _splice

        if prop == 'concat':
            def _concat(*others):
                result = JSArray(list(arr))
                for o in others:
                    if isinstance(o, JSArray):
                        result.extend(list(o))
                    else:
                        result.append(o)
                return result
            return _concat

        if prop == 'join':
            def _join(sep=UNDEFINED):
                s = ',' if sep is UNDEFINED else js_to_string(sep)
                return s.join('' if (x is UNDEFINED or x is JS_NULL or x is None) else js_to_string(x) for x in arr)
            return _join

        if prop == 'indexOf':
            def _indexOf(val, from_=UNDEFINED):
                fr = 0 if from_ is UNDEFINED else int(js_to_number(from_)) if isinstance(from_, float) else int(from_)
                for i in range(max(0, fr), len(arr)):
                    if js_strict_equal(arr[i], val):
                        return float(i)
                return -1.0
            return _indexOf

        if prop == 'lastIndexOf':
            def _lastIndexOf(val, from_=UNDEFINED):
                fr = len(arr) - 1 if from_ is UNDEFINED else (int(js_to_number(from_)) if isinstance(from_, float) else int(from_))
                for i in range(fr, -1, -1):
                    if js_strict_equal(arr[i], val):
                        return float(i)
                return -1.0
            return _lastIndexOf

        if prop == 'includes':
            def _includes(val, from_=0):
                for item in arr:
                    if js_strict_equal(item, val):
                        return True
                return False
            return _includes

        if prop == 'find':
            def _find(fn):
                for i, item in enumerate(arr):
                    if js_to_bool(self._call(fn, [item, float(i), arr])):
                        return item
                return UNDEFINED
            return _find

        if prop == 'findIndex':
            def _findIndex(fn):
                for i, item in enumerate(arr):
                    if js_to_bool(self._call(fn, [item, float(i), arr])):
                        return float(i)
                return -1.0
            return _findIndex

        if prop == 'filter':
            def _filter(fn):
                return JSArray([item for i, item in enumerate(arr)
                                if js_to_bool(self._call(fn, [item, float(i), arr]))])
            return _filter

        if prop == 'map':
            def _map(fn):
                return JSArray([self._call(fn, [item, float(i), arr]) for i, item in enumerate(arr)])
            return _map

        if prop == 'forEach':
            def _forEach(fn):
                for i, item in enumerate(arr):
                    self._call(fn, [item, float(i), arr])
                return UNDEFINED
            return _forEach

        if prop == 'reduce':
            def _reduce(fn, initial=UNDEFINED):
                items = list(arr)
                if initial is UNDEFINED:
                    if not items: raise ThrowSignal(self._make_error('Reduce of empty array with no initial value'))
                    acc = items[0]
                    items = items[1:]
                else:
                    acc = initial
                for i, item in enumerate(items):
                    acc = self._call(fn, [acc, item, float(i), arr])
                return acc
            return _reduce

        if prop == 'reduceRight':
            def _reduceRight(fn, initial=UNDEFINED):
                items = list(reversed(arr))
                if initial is UNDEFINED:
                    acc = items[0]
                    items = items[1:]
                else:
                    acc = initial
                for i, item in enumerate(items):
                    acc = self._call(fn, [acc, item, float(len(arr)-1-i), arr])
                return acc
            return _reduceRight

        if prop == 'some':
            def _some(fn):
                return any(js_to_bool(self._call(fn, [item, float(i), arr])) for i, item in enumerate(arr))
            return _some

        if prop == 'every':
            def _every(fn):
                return all(js_to_bool(self._call(fn, [item, float(i), arr])) for i, item in enumerate(arr))
            return _every

        if prop == 'flat':
            def _flat(depth=1):
                def flatten(a, d):
                    result = JSArray()
                    for item in a:
                        if isinstance(item, JSArray) and d > 0:
                            result.extend(flatten(item, d-1))
                        else:
                            result.append(item)
                    return result
                return flatten(arr, int(js_to_number(depth)) if depth is not UNDEFINED else 1)
            return _flat

        if prop == 'flatMap':
            def _flatMap(fn):
                result = JSArray()
                for i, item in enumerate(arr):
                    mapped = self._call(fn, [item, float(i), arr])
                    if isinstance(mapped, JSArray):
                        result.extend(list(mapped))
                    else:
                        result.append(mapped)
                return result
            return _flatMap

        if prop == 'fill':
            def _fill(val, start=UNDEFINED, end=UNDEFINED):
                n = len(arr)
                st = 0 if start is UNDEFINED else int(js_to_number(start))
                en = n if end is UNDEFINED else int(js_to_number(end))
                if st < 0: st = max(0, n + st)
                if en < 0: en = max(0, n + en)
                for i in range(st, min(en, n)):
                    arr[i] = val
                return arr
            return _fill

        if prop == 'keys': return lambda: JSArray([float(i) for i in range(len(arr))])
        if prop == 'values': return lambda: JSArray(list(arr))
        if prop == 'entries': return lambda: JSArray([JSArray([float(i), v]) for i, v in enumerate(arr)])

        if prop == 'toString': return lambda: ','.join(js_to_string(x) for x in arr)
        if prop == 'at':
            def _at(i):
                idx = int(js_to_number(i))
                if idx < 0: idx = len(arr) + idx
                return arr[idx] if 0 <= idx < len(arr) else UNDEFINED
            return _at

        if prop == 'copyWithin':
            def _copyWithin(target, start=0, end=UNDEFINED):
                n = len(arr)
                t = int(js_to_number(target))
                s = int(js_to_number(start))
                e = n if end is UNDEFINED else int(js_to_number(end))
                chunk = list(arr[s:e])
                for i, v in enumerate(chunk):
                    if t + i < n:
                        arr[t + i] = v
                return arr
            return _copyWithin

        # Check custom props
        if prop in arr.props:
            return arr.props[prop]

        # Index access
        try:
            idx = int(prop)
            return arr[idx] if 0 <= idx < len(arr) else UNDEFINED
        except:
            pass

        return UNDEFINED


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

def run_js(source: str) -> str:
    tokens = tokenize(source)
    parser = Parser(tokens)
    ast = parser.parse()
    interp = Interpreter()
    try:
        interp.run(ast)
    except ThrowSignal as e:
        err = e.value
        msg = err.get('message') if isinstance(err, JSObject) else js_to_string(err)
        name = err.get('name') if isinstance(err, JSObject) else 'Error'
        print(f"Uncaught {name}: {msg}", file=sys.stderr)
    except Exception as e:
        print(f"Runtime error: {e}", file=sys.stderr)
    return '\n'.join(interp.output)


def main():
    if len(sys.argv) < 2 or sys.argv[1] == '-':
        # Read from stdin
        source = sys.stdin.read()
    else:
        path = sys.argv[1]
        try:
            with open(path, 'r', encoding='utf-8') as f:
                source = f.read()
        except FileNotFoundError:
            print(f"Error: File not found: {path}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)

    success = True
    tokens = tokenize(source)
    parser = Parser(tokens)
    ast = parser.parse()
    interp = Interpreter()
    try:
        interp.run(ast)
    except ThrowSignal as e:
        err = e.value
        msg = err.get('message') if isinstance(err, JSObject) else js_to_string(err)
        name = err.get('name') if isinstance(err, JSObject) else 'Error'
        print(f"Uncaught {name}: {msg}", file=sys.stderr)
        success = False
    except (LexError, ParseError) as e:
        print(f"SyntaxError: {e}", file=sys.stderr)
        success = False
    except Exception as e:
        print(f"Runtime error: {e}", file=sys.stderr)
        success = False

    output = '\n'.join(interp.output)
    if output:
        print(output)

    if not success:
        sys.exit(1)


if __name__ == '__main__':
    main()
