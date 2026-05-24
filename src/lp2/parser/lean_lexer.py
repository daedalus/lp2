from __future__ import annotations
from dataclasses import dataclass
from typing import NoReturn


@dataclass
class Token:
    kind: str
    value: str
    pos: int
    line: int
    col: int

    def __repr__(self):
        return f"Token({self.kind}, {self.value!r})"


KW_MAP = {
    "def": "DEF",
    "theorem": "THEOREM",
    "lemma": "LEMMA",
    "inductive": "INDUCTIVE",
    "structure": "STRUCTURE",
    "class": "CLASS",
    "instance": "INSTANCE",
    "axiom": "AXIOM",
    "example": "EXAMPLE",
    "open": "OPEN",
    "namespace": "NAMESPACE",
    "section": "SECTION",
    "variable": "VARIABLE",
    "mutual": "MUTUAL",
    "partial": "PARTIAL",
    "nonrec": "NONREC",
    "private": "PRIVATE",
    "protected": "PROTECTED",
    "public": "PUBLIC",
    "fun": "FUN",
    "λ": "FUN",
    "forall": "FORALL",
    "∀": "FORALL",
    "match": "MATCH",
    "with": "WITH",
    "=>": "ARROW",
    "if": "IF",
    "then": "THEN",
    "else": "ELSE",
    "let": "LET",
    "in": "IN",
    "have": "HAVE",
    "show": "SHOW",
    "calc": "CALC",
    "do": "DO",
    "return": "RETURN",
    "mut": "MUT",
    "where": "WHERE",
    "true": "TRUE",
    "false": "FALSE",
    "by": "BY",
    ":=": "COLONEQ",
    "=": "EQ",
    ":": "COLON",
    "::": "DOUBLECOLON",
    "→": "RARROW",
    "|": "PIPE",
    ",": "COMMA",
    ".": "DOT",
    "(": "LPAREN",
    ")": "RPAREN",
    "[": "LBRACK",
    "]": "RBRACK",
    "{": "LBRACE",
    "}": "RBRACE",
    "_": "WILD",
    "#eval": "HASH_EVAL",
    "#check": "HASH_CHECK",
    "#print": "HASH_PRINT",
}


class LeanLexer:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: list[Token] = []
        self._tokenize()

    def _error(self, msg: str) -> NoReturn:
        raise SyntaxError(f"{msg} at line {self.line}, col {self.col}")

    def _peek(self, offset: int = 0) -> str | None:
        idx = self.pos + offset
        return self.source[idx] if idx < len(self.source) else None

    def _advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _skip_ws(self) -> None:
        while self.pos < len(self.source) and self.source[self.pos] in " \t\n\r":
            self._advance()

    def _skip_comment(self) -> None:
        if self.source[self.pos : self.pos + 2] == "--":
            while self.pos < len(self.source) and self.source[self.pos] != "\n":
                self._advance()
        elif self.source[self.pos : self.pos + 2] == "/-":
            self.pos += 2
            depth = 1
            while self.pos < len(self.source) and depth > 0:
                if self.source[self.pos : self.pos + 2] == "/-":
                    depth += 1
                    self.pos += 2
                elif self.source[self.pos : self.pos + 2] == "-/":
                    depth -= 1
                    self.pos += 2
                else:
                    self._advance()

    def _read_string(self, quote: str) -> str:
        result = []
        while self.pos < len(self.source):
            ch = self._advance()
            if ch == "\\":
                nxt = self._advance() if self.pos < len(self.source) else ""
                esc = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"', "'": "'"}
                result.append(esc.get(nxt, nxt))
            elif ch == quote:
                return "".join(result)
            else:
                result.append(ch)
        self._error("Unterminated string")

    def _read_number(self) -> int:
        start = self.pos
        is_float = False
        while self.pos < len(self.source):
            ch: str | None = self.source[self.pos]
            if ch is None:
                break
            if ch.isdigit():
                self._advance()
            elif (
                ch == "."
                and self.pos + 1 < len(self.source)
                and self.source[self.pos + 1].isdigit()
            ):
                is_float = True
                self._advance()
            elif ch in "eE" and is_float:
                self._advance()
                nxt = self._peek()
                if nxt is not None and nxt in "+-":
                    self._advance()
            elif ch in "eE" and not is_float:
                # allow 1e10, 1E-5, etc. (no decimal point required)
                is_float = True
                self._advance()
                nxt = self._peek()
                if nxt is not None and nxt in "+-":
                    self._advance()
            else:
                break
        return start

    _TRIPLE = {"&&&": "AMPAMPAMP", "|||": "PIPEPIPEPIPE", "<<<": "LTLTLT", ">>>": "GTGTGT"}

    _MULTI = {
        "->": "RARROW", "=>": "ARROW", "::": "DOUBLECOLON",
        ":=": "COLONEQ", "++": "PLUSPLUS", "|>": "PIPEOP", "<|": "PIPEOP",
        "≥": "GE", "≤": "LE", "≠": "NE",
        "<=": "LE", ">=": "GE", "!=": "NE", "==": "DEQ",
        "&&": "AMPAMP", "||": "PIPEPIPE", "<<": "LTLT", ">>": "GTGT",
    }

    _UNICODE_SINGLE = {"→": "RARROW", "≤": "LE", "≥": "GE", "≠": "NE", "∀": "FORALL", "λ": "FUN"}

    _SINGLE = {
        ";": "SEMI", "(": "LPAREN", ")": "RPAREN",
        "[": "LBRACK", "]": "RBRACK", "{": "LBRACE", "}": "RBRACE",
        ":": "COLON", ",": "COMMA", ".": "DOT",
        "|": "PIPE", "=": "EQ", "+": "PLUS", "-": "MINUS",
        "*": "STAR", "/": "SLASH", "%": "PERCENT", "^": "HAT",
        "<": "LT", ">": "GT", "!": "BANG",
        "@": "AT", "$": "DOLLAR", "~": "TILDE", "&": "AMP",
        "?": "QMARK", "#": "HASH",
    }

    def _tokenize(self) -> None:
        while self.pos < len(self.source):
            self._tokenize_one()
        self.tokens.append(Token("EOF", "", self.pos, self.line, self.col))

    def _tokenize_one(self) -> None:
        pos, line, col = self.pos, self.line, self.col
        ch = self._peek()
        if ch is None:
            return

        if ch in " \t\n\r":
            self._skip_ws()
            return

        if (ch == "-" or ch == "/") and self._peek(1) == "-":
            self._skip_comment()
            return

        if ch == '"':
            self._advance()
            self.tokens.append(Token("STR", self._read_string('"'), pos, line, col))
            return

        if ch == "'":
            self._tokenize_char(pos, line, col)
            return

        if ch.isdigit():
            self._tokenize_number(pos, line, col)
            return

        if ch.isalpha() or ch in "_λ∀":
            self._tokenize_ident(line, col)
            return

        if self._tokenize_tri(pos, line, col):
            return

        if self._tokenize_multi(pos, line, col):
            return

        if self._tokenize_single(ch, pos, line, col):
            return

        self._error(f"Unexpected character {ch!r}")

    def _tokenize_single(self, ch: str, pos: int, line: int, col: int) -> bool:
        if ch in self._UNICODE_SINGLE:
            self._advance()
            self.tokens.append(Token(self._UNICODE_SINGLE[ch], ch, pos, line, col))
            return True
        if ch in self._SINGLE:
            self._advance()
            self.tokens.append(Token(self._SINGLE[ch], ch, pos, line, col))
            return True
        return False

    def _tokenize_char(self, pos: int, line: int, col: int) -> None:
        self._advance()
        if self._peek() == "\\":
            self._advance()
            c = self._advance()
        else:
            c = self._advance()
        if self._advance() != "'":
            self._error("Expected closing single quote")
        self.tokens.append(Token("CHAR", c, pos, line, col))

    def _tokenize_number(self, pos: int, line: int, col: int) -> None:
        start = self._read_number()
        raw = self.source[start : self.pos]
        if "." in raw or "e" in raw.lower():
            self.tokens.append(Token("FLOAT", raw, start, line, col))
        else:
            self.tokens.append(Token("NUM", raw, start, line, col))

    def _tokenize_ident(self, line: int, col: int) -> None:
        ident_start = self.pos
        while self.pos < len(self.source):
            c = self._peek()
            if c is None:
                break
            if c.isalnum() or c in "_'λ∀":
                self._advance()
            else:
                break
        word = self.source[ident_start : self.pos]
        if word == "λ":
            self.tokens.append(Token("FUN", word, ident_start, line, col))
        elif word == "∀":
            self.tokens.append(Token("FORALL", word, ident_start, line, col))
        elif word == "→":
            self.tokens.append(Token("RARROW", word, ident_start, line, col))
        elif word in ("true", "false"):
            self.tokens.append(Token("BOOL", word, ident_start, line, col))
        elif word in KW_MAP:
            self.tokens.append(Token(KW_MAP[word], word, ident_start, line, col))
        else:
            self.tokens.append(Token("ID", word, ident_start, line, col))

    def _tokenize_tri(self, pos: int, line: int, col: int) -> bool:
        tri = self.source[self.pos : self.pos + 3]
        if tri not in self._TRIPLE:
            return False
        kind = self._TRIPLE[tri]
        self.pos += 3
        self.col += 3
        self.tokens.append(Token(kind, tri, pos, line, col))
        return True

    def _tokenize_multi(self, pos: int, line: int, col: int) -> bool:
        two = self.source[self.pos : self.pos + 2]
        if two not in self._MULTI:
            return False
        kind = self._MULTI[two]
        self.pos += 2
        self.col += 2
        self.tokens.append(Token(kind, two, pos, line, col))
        return True
