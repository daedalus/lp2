from __future__ import annotations

from lp2.ast.lean4_ast import *
from lp2.parser.lean_lexer import LeanLexer, Token

PRECEDENCE = {
    "IFF": 2,
    "RARROW": 1,
    "COLON": 2,
    "PIPEPIPE": 2,
    "PIPEPIPEPIPE": 2,
    "AMPAMP": 3,
    "AMPAMPAMP": 3,
    "AMP": 3,
    "PIPEOP": 3,
    "EQ": 4,
    "DEQ": 4,
    "LT": 4,
    "GT": 4,
    "LE": 4,
    "GE": 4,
    "NE": 4,
    "DOUBLECOLON": 7,
    "LTLT": 7,
    "GTGT": 7,
    "LTLTLT": 7,
    "GTGTGT": 7,
    "BIND": 7,
    "PLUS": 8,
    "PLUSPLUS": 8,
    "MINUS": 8,
    "STAR": 9,
    "SLASH": 9,
    "PERCENT": 9,
    "HAT": 10,
    "BANG": 11,
    "IMG": 7,
    "BACKSLASH": 7,
    "SQCAP": 7,
    "IN": 4,
}


BINARY_OPS = {
    "PLUS": "+",
    "MINUS": "-",
    "STAR": "*",
    "SLASH": "/",
    "PERCENT": "%",
    "EQ": "=",
    "DEQ": "==",
    "LT": "<",
    "GT": ">",
    "LE": "≤",
    "GE": "≥",
    "NE": "≠",
    "DOUBLECOLON": "::",
    "PLUSPLUS": "++",
    "AMP": "&&",
    "AMPAMP": "&&",
    "AMPAMPAMP": "&&&",
    "PIPEPIPE": "||",
    "PIPEPIPEPIPE": "|||",
    "LTLT": "<<",
    "GTGT": ">>",
    "LTLTLT": "<<<",
    "GTGTGT": ">>>",
    "BIND": ">>=",
    "HAT": "^",
    "RARROW": "→",
    "IFF": "↔",
    "PIPEOP": "|>",
    "IMG": "''",
    "BACKSLASH": "\\",
    "SQCAP": "⊓",
    "IN": "∈",
}


class LeanParser:
    def __init__(self, source: str):
        self.lexer = LeanLexer(source)
        self.tokens = self.lexer.tokens
        self.pos = 0

    def _peek(self, offset: int = 0) -> Token:
        idx = self.pos + offset
        if idx >= len(self.tokens):
            return Token(kind="EOF", value=None, pos=-1, line=-1, col=-1)
        return self.tokens[idx]

    def _advance(self) -> Token:
        if self.pos >= len(self.tokens):
            return Token(kind="EOF", value=None, pos=-1, line=-1, col=-1)
        t = self.tokens[self.pos]
        self.pos += 1
        return t

    def _expect(self, kind: str, value: str | None = None) -> Token:
        t = self._peek()
        if t.kind != kind or (value is not None and t.value != value):
            raise SyntaxError(
                f"Expected {kind}({value}), got {t.kind}({t.value}) at line {t.line}, col {t.col}"
            )
        return self._advance()

    def _maybe(self, kind: str, value: str | None = None) -> bool:
        t = self._peek()
        if t.kind == kind and (value is None or t.value == value):
            self._advance()
            return True
        return False

    def _skip_to(self, kinds: set[str]):
        while self._peek().kind not in kinds and self._peek().kind != "EOF":
            self._advance()

    # ---- Shared top-level command dispatch ----

    _MODULE_DISPATCH = {
        "OPEN": "_parse_open",
        "DEF": "_parse_def",
        "THEOREM": "_parse_def",
        "LEMMA": "_parse_def",
        "INDUCTIVE": "_parse_inductive",
        "STRUCTURE": "_parse_structure",
        "CLASS": "_parse_class",
        "INSTANCE": "_parse_instance",
        "AXIOM": "_parse_axiom",
        "EXAMPLE": "_parse_example",
        "NAMESPACE": "_parse_namespace",
        "SECTION": "_parse_section",
        "VARIABLE": "_parse_variable",
    }

    def _skip_attributes_and_visibility(self):
        """Skip @[attr] blocks and public/private/protected modifiers before a command."""
        while True:
            if self._peek().kind == "AT":
                self._advance()  # consume @
                if self._peek().kind == "LBRACK":
                    self._advance()  # consume [
                    depth = 1
                    while depth > 0 and self._peek().kind != "EOF":
                        if self._peek().kind == "LBRACK":
                            depth += 1
                        elif self._peek().kind == "RBRACK":
                            depth -= 1
                        self._advance()
                continue
            if self._peek().kind in ("PUBLIC", "PRIVATE", "PROTECTED"):
                self._advance()
                continue
            break

    def _parse_cmd(self) -> LeanCommand | None:
        """Parse a single top-level command, or return None if no command is recognized.

        Shared by parse_module, _parse_section, and _parse_namespace.
        Catches SyntaxError to gracefully degrade on unknown syntax.
        """
        self._skip_attributes_and_visibility()
        kind = self._peek().kind
        handler = self._MODULE_DISPATCH.get(kind)
        if handler is not None:
            try:
                return getattr(self, handler)()
            except (SyntaxError, IndexError, RuntimeError):
                return None
        if kind in ("HASH_EVAL", "HASH_CHECK"):
            self._advance()
            return LeanExample(expr=self._parse_expr())
        return None

    def parse_module(self) -> LeanModule:
        imports: list[LeanOpen] = []
        body: list[LeanNode] = []
        # skip optional `module` header
        if self._peek().value == "module":
            self._advance()
        while self._peek().kind != "EOF":
            kind = self._peek().kind
            local = False
            if kind == "LOCAL":
                local = True
                self._advance()
                kind = self._peek().kind
            cmd = self._parse_cmd()
            if cmd is not None:
                if local and isinstance(cmd, LeanInstance):
                    cmd.is_local = True
                body.append(cmd)
            else:
                try:
                    body.append(self._parse_def())
                except (SyntaxError, IndexError):
                    self._skip_to(
                        {
                            "EOF",
                            "DEF",
                            "THEOREM",
                            "LEMMA",
                            "INDUCTIVE",
                            "STRUCTURE",
                            "CLASS",
                            "INSTANCE",
                            "AXIOM",
                            "EXAMPLE",
                            "NAMESPACE",
                            "SECTION",
                            "OPEN",
                            "VARIABLE",
                            "MUTUAL",
                            "PARTIAL",
                            "HASH_EVAL",
                            "HASH_CHECK",
                        }
                    )
        return LeanModule(imports=imports, body=body)

    def _parse_def(self) -> LeanDef:
        is_theorem = self._maybe("THEOREM")
        is_lemma = self._maybe("LEMMA")
        is_mutual = self._maybe("MUTUAL")
        is_partial = self._maybe("PARTIAL")
        if not (is_theorem or is_lemma):
            self._expect("DEF")
        name_token = self._expect("ID")
        name = name_token.value
        # Handle qualified names like dist.triangle_inequality
        while self._peek().kind == "DOT" and self._peek(1).kind == "ID":
            self._advance()  # consume DOT
            name += "." + self._expect("ID").value

        params = []
        while self._peek().kind in ("ID", "LPAREN", "LBRACE", "LBRACK"):
            if self._peek().kind == "ID" and self._peek().value not in (":", ":="):
                if self._pos_is_binder():
                    params.extend(self._parse_binders())
                else:
                    ident = self._parse_prefix()
                    if isinstance(ident, LeanIdent):
                        params.append(LeanParam(name=ident.name, type=None))
                    break
            else:
                params.extend(self._parse_binders())

        return_type = None
        if self._maybe("COLON"):
            return_type = self._parse_expr()

        sig_only = False
        value = None
        if self._maybe("COLONEQ") or self._maybe("EQ"):
            if self._peek().kind == "BY":
                self._advance()
                value = LeanBy(tactic=self._parse_tactic())
            else:
                value = self._parse_expr()
        elif self._peek().kind in (
            "DEF",
            "THEOREM",
            "LEMMA",
            "ID",
            "EOF",
            "INDUCTIVE",
            "STRUCTURE",
            "CLASS",
        ):
            sig_only = True
        else:
            sig_only = True

        return LeanDef(
            name=name,
            params=params,
            return_type=return_type,
            value=value,
            is_theorem=is_theorem,
            is_lemma=is_lemma,
            is_mutual=is_mutual,
            sig_only=sig_only,
            is_partial=is_partial,
        )

    def _pos_is_binder(self) -> bool:
        if self._peek().kind == "LPAREN" or self._peek().kind == "LBRACE":
            save = self.pos
            try:
                self._parse_binders()
                return self._peek().kind != "EOF"
            except (SyntaxError, IndexError):
                return False
            finally:
                self.pos = save
        return False

    def _parse_binders(self) -> list[LeanParam]:
        params: list[LeanParam] = []
        while self._peek().kind in ("LPAREN", "LBRACE", "LBRACK"):
            open_kind = self._peek().kind
            explicit = open_kind == "LPAREN"
            implicit = open_kind == "LBRACE"
            inst_imp = open_kind == "LBRACK"
            self._advance()

            names = []
            while self._peek().kind == "ID":
                names.append(self._advance().value)
                self._maybe("COMMA")

            if self._peek().kind == "COLON":
                self._advance()
                typ = self._parse_expr()
            else:
                typ = None

            close_kind = {"LPAREN": "RPAREN", "LBRACE": "RBRACE", "LBRACK": "RBRACK"}[
                open_kind
            ]
            self._expect(close_kind)

            for name in names:
                params.append(LeanParam(name=name, type=typ, explicit=explicit))
            if not names and typ is None:
                params.append(LeanParam(name="_", type=None, explicit=explicit))
        return params

    def _parse_inductive(self) -> LeanInductive:
        self._expect("INDUCTIVE")
        name = self._expect("ID").value
        params = []
        while self._peek().kind in ("LPAREN", "LBRACE", "LBRACK"):
            params.extend(self._parse_binders())
        typ = LeanSort()
        if self._maybe("COLON"):
            typ = self._parse_expr()
        else:
            typ = LeanSort()

        if self._peek().kind == "WHERE":
            self._advance()
        elif self._peek().kind == "COLONEQ":
            self._advance()
        elif self._peek().kind == "EQ":
            self._advance()
        if self._peek().kind == "PIPE":
            self._maybe("PIPE")

        constructors = []
        while self._peek().kind == "ID":
            ctor_name = self._advance().value
            ctor_fields = []
            while self._peek().kind in ("LPAREN", "LBRACE", "LBRACK"):
                ctor_fields.extend(self._parse_binders())
            constructors.append(LeanConstructor(name=ctor_name, fields=ctor_fields))
            self._maybe("PIPE")
        return LeanInductive(
            name=name, params=params, type=typ, constructors=constructors
        )

    def _parse_structure(self) -> LeanStructure:
        self._expect("STRUCTURE")
        name = self._expect("ID").value
        params = []
        while self._peek().kind in ("LPAREN", "LBRACE", "LBRACK"):
            params.extend(self._parse_binders())
        extends = []
        if self._maybe("EXTENDS"):
            extends.append(self._parse_expr())
        self._expect("COLON") if self._peek().kind == "COLON" else None
        fields = []
        while self._peek().kind == "ID":
            field_name = self._advance().value
            self._expect("COLON")
            field_type = self._parse_expr()
            fields.append(LeanParam(name=field_name, type=field_type))
        return LeanStructure(name=name, params=params, extends=extends, fields=fields)

    def _parse_class(self) -> LeanClass:
        self._expect("CLASS")
        name = self._expect("ID").value
        params = []
        while self._peek().kind in ("LPAREN", "LBRACE", "LBRACK"):
            params.extend(self._parse_binders())
        extends = []
        if self._maybe("EXTENDS"):
            extends.append(self._parse_expr())
        fields = []
        while self._peek().kind == "ID":
            field_name = self._advance().value
            self._expect("COLON")
            field_type = self._parse_expr()
            fields.append(LeanParam(name=field_name, type=field_type))
        return LeanClass(name=name, params=params, extends=extends, fields=fields)

    def _parse_instance(self) -> LeanInstance:
        self._expect("INSTANCE")
        name = self._advance().value if self._peek().kind == "ID" else "_"
        params = []
        while self._peek().kind in ("LPAREN", "LBRACE", "LBRACK"):
            params.extend(self._parse_binders())
        self._expect("COLON")
        typ = self._parse_expr()
        if self._peek().kind in ("COLONEQ", "EQ"):
            self._advance()
        methods = []
        if self._peek().kind == "WHERE":
            self._advance()
            while self._peek().kind == "ID":
                name_tok = self._expect("ID")
                mt_name = name_tok.value
                mt_params = []
                while self._peek().kind == "ID":
                    mt_params.append(
                        LeanParam(name=self._expect("ID").value, type=None)
                    )
                self._expect("COLONEQ")
                mt_val = self._parse_expr()
                methods.append(
                    LeanDef(
                        name=mt_name, params=mt_params, return_type=None, value=mt_val
                    )
                )
        elif self._peek().kind in ("DEF",):
            while self._peek().kind == "DEF":
                methods.append(self._parse_def())
        else:
            # If there was a := or =, consume the value expression
            pass
        return LeanInstance(name=name, params=params, type=typ, methods=methods)

    def _parse_axiom(self) -> LeanAxiom:
        self._expect("AXIOM")
        name = self._expect("ID").value
        params = []
        while self._peek().kind in ("LPAREN", "LBRACE", "LBRACK"):
            params.extend(self._parse_binders())
        self._expect("COLON")
        typ = self._parse_expr()
        return LeanAxiom(name=name, params=params, type=typ)

    def _parse_example(self) -> LeanExample:
        self._expect("EXAMPLE")
        expr = self._parse_expr()
        return LeanExample(expr=expr)

    def _parse_open(self) -> LeanOpen:
        self._expect("OPEN")
        names = []
        while self._peek().kind == "ID":
            names.append(self._advance().value)
        return LeanOpen(names=names)

    def _parse_namespace(self) -> LeanNamespace:
        self._expect("NAMESPACE")
        name = self._expect("ID").value
        commands = []
        max_iter = 5000
        iter_count = 0
        while self._peek().kind not in ("EOF",) and self._peek().value != "end":
            if iter_count > max_iter:
                raise RuntimeError("_parse_namespace: max iterations exceeded")
            iter_count += 1
            cmd = self._parse_cmd()
            if cmd is not None:
                commands.append(cmd)
            else:
                self._advance()
        if self._peek().value == "end":
            self._advance()
        return LeanNamespace(name=name, commands=commands)

    def _parse_section(self) -> LeanSection:
        self._expect("SECTION")
        params = []
        while self._peek().kind in ("LPAREN", "LBRACE", "LBRACK"):
            params.extend(self._parse_binders())
        commands = []
        max_iter = 10000
        iter_count = 0
        while self._peek().kind not in ("EOF",) and self._peek().value != "end":
            if iter_count > max_iter:
                raise RuntimeError("_parse_section: max iterations exceeded")
            iter_count += 1
            cmd = self._parse_cmd()
            if cmd is not None:
                commands.append(cmd)
            else:
                self._advance()
        if self._peek().value == "end":
            self._advance()
        return LeanSection(params=params, commands=commands)

    def _parse_variable(self) -> LeanVariable:
        self._expect("VARIABLE")
        params = []
        while self._peek().kind in ("LPAREN", "LBRACE", "LBRACK", "ID"):
            if self._peek().kind == "ID":
                name = self._advance().value
                self._expect("COLON")
                typ = self._parse_expr()
                params.append(LeanParam(name=name, type=typ))
            else:
                params.extend(self._parse_binders())
        return LeanVariable(params=params)

    # ---- Expression Parsing (Pratt-style) ----

    _TOK_IS_ATOM = frozenset(
        {
            "ID",
            "NUM",
            "STR",
            "BOOL",
            "FLOAT",
            "CHAR",
            "LPAREN",
            "LBRACK",
            "LBRACE",
            "WILD",
            "IN",
            "UNION",
            "TURNSTILE",
            "TRIANGLE",
            "LANGLE",
            "RANGLE",
            "EXISTS",
            "PROD",
            "COMPOSE",
            "DIVIDES",
            "EQV",
            "BOT",
            "NOTIN",
            "SUBSET",
            "BIGUNION",
            "UPARROW",
            "SUM",
            "DOWNARROW",
            "AT",
            "BULLET",
            "EMPTYSET",
            "TOP",
            "BIGINF",
            "BY",
            "BACKTICK",
            "HASH",
            "SQUNION",
            "BIGUNION2",
            "INTERSECT",
            "BACKSLASH",
            "IMG",
            "SQCAP",
            "BIGINTER",
            "SUPMINUS",
            "INFINITY",
            "INTEGRAL",
            "PARTIAL",
            "SQRT",
            "LFLOOR",
            "CIRCLE",
            "ANGLE",
            "LCEIL",
            "SUPSET",
            "SQUARE",
            "PRIME",
            "GRADIENT",
            "NAND",
            "YEN",
            "FLAT",
            "RETURN",
            "BALLOT_X",
            "RFLOOR",
            "RCEIL",
            "DOTDOTDOT",
        }
    )

    def _handle_binop(self, lhs: LeanExpr, prec: int, op: str) -> LeanExpr:
        # Left-associative by default: RHS must be at least prec + 1
        # Right-assoc operators (→, ::) pass prec directly so A→B→C = A→(B→C)
        rhs_prec = prec if op in ("→", "::") else prec + 1
        rhs = self._parse_expr(rhs_prec)
        if op == "→":
            return LeanTypeArrow(from_type=lhs, to_type=rhs)
        if op == ":":
            return LeanTypeSpec(expr=lhs, type=rhs)
        return LeanBinOp(left=lhs, op=op, right=rhs)

    def _parse_expr_until(self, stop_kinds: set[str]) -> LeanExpr:
        if self._peek().kind in stop_kinds:
            raise SyntaxError(
                f"Unexpected stop token {self._peek().kind}({self._peek().value})"
                f" at line {self._peek().line}, col {self._peek().col}"
            )
        lhs = self._parse_prefix()
        if lhs is None:
            t = self._peek()
            raise SyntaxError(
                f"Unexpected token {t.kind}({t.value}) at line {t.line}, col {t.col}"
            )

        while True:
            tok = self._peek()
            kind = tok.kind
            if kind in stop_kinds:
                break
            if kind in BINARY_OPS and PRECEDENCE.get(kind, 0) >= 0:
                op = BINARY_OPS[kind]
                prec = PRECEDENCE[kind]
                self._advance()
                rhs_prec = prec if op in ("→", "::") else prec + 1
                rhs = self._parse_expr_until(stop_kinds)
                if op == "→":
                    lhs = LeanTypeArrow(from_type=lhs, to_type=rhs)
                elif op == ":":
                    lhs = LeanTypeSpec(expr=lhs, type=rhs)
                else:
                    lhs = LeanBinOp(left=lhs, op=op, right=rhs)
            elif kind == "DOT":
                self._advance()
                if self._peek().kind == "NUM":
                    lhs = LeanProj(expr=lhs, field=self._advance().value)
                else:
                    lhs = LeanProj(expr=lhs, field=self._expect("ID").value)
            elif kind in self._TOK_IS_ATOM and PRECEDENCE.get("APP", 13) >= 0:
                arg = self._parse_prefix()
                if arg is None:
                    break
                lhs = LeanApp(func=lhs, arg=arg)
            else:
                break

        return lhs

    def _parse_expr(self, min_prec: int = 0) -> LeanExpr:
        lhs = self._parse_prefix()
        if lhs is None:
            t = self._peek()
            raise SyntaxError(
                f"Unexpected token {t.kind}({t.value}) at line {t.line}, col {t.col}"
            )

        while True:
            tok = self._peek()
            kind = tok.kind
            if kind in BINARY_OPS and PRECEDENCE.get(kind, 0) >= min_prec:
                op = BINARY_OPS[kind]
                prec = PRECEDENCE[kind]
                self._advance()
                lhs = self._handle_binop(lhs, prec, op)
            elif kind == "DOT":
                self._advance()
                if self._peek().kind == "NUM":
                    lhs = LeanProj(expr=lhs, field=self._advance().value)
                else:
                    lhs = LeanProj(expr=lhs, field=self._expect("ID").value)
            elif kind in self._TOK_IS_ATOM and PRECEDENCE.get("APP", 13) >= min_prec:
                arg = self._parse_prefix()
                if arg is None:
                    break
                lhs = LeanApp(func=lhs, arg=arg)
            else:
                break

        return lhs

    def _pid(self) -> LeanExpr:
        return LeanIdent(name=self._advance().value)

    def _pnum(self) -> LeanExpr:
        n_val = int(self._advance().value)
        return LeanNum(value=n_val, is_nat=n_val >= 0)

    def _pfloat(self) -> LeanExpr:
        return LeanFloat(value=float(self._advance().value))

    def _pstr(self) -> LeanExpr:
        return LeanString(value=self._advance().value)

    def _pchar(self) -> LeanExpr:
        return LeanChar(value=self._advance().value)

    def _pbool(self) -> LeanExpr:
        return LeanBool(value=self._advance().value == "true")

    def _pwild(self) -> LeanExpr:
        self._advance()
        return LeanHole()

    def _plparen(self) -> LeanExpr:
        self._advance()
        if self._peek().kind == "RPAREN":
            self._advance()
            return LeanUnit()
        if self._maybe("COLON"):
            typ = self._parse_expr()
            if self._maybe("RPAREN"):
                return LeanTypeSpec(expr=LeanHole(), type=typ)
            self._expect("RPAREN")
        # Named argument: (name := expr)
        if self._peek().kind == "ID" and self._peek(1).kind == "COLONEQ":
            name = self._advance().value
            self._advance()  # consume COLONEQ
            value = self._parse_expr()
            self._expect("RPAREN")
            return LeanNamedArg(name=name, value=value)
        expr = self._parse_expr()
        while self._maybe("COMMA"):
            elts = [expr]
            elts.append(self._parse_expr())
            while self._maybe("COMMA"):
                elts.append(self._parse_expr())
            self._expect("RPAREN")
            return LeanTupleLit(elts=elts)
        if self._maybe("COLON"):
            typ = self._parse_expr()
            expr = LeanTypeSpec(expr=expr, type=typ)
        self._expect("RPAREN")
        return expr

    def _plbrack(self) -> LeanExpr:
        self._advance()
        elts = []
        if self._peek().kind != "RBRACK":
            elts.append(self._parse_expr())
            while self._maybe("COMMA"):
                elts.append(self._parse_expr())
        self._expect("RBRACK")
        return LeanListLit(elts=elts)

    def _plbrace(self) -> LeanExpr:
        self._advance()
        if self._peek().kind == "RBRACE":
            self._advance()
            return LeanUnit()
        if self._peek().kind == "ID" and self._peek(1).kind == "COLONEQ":
            return self._parse_struct_inst()
        expr = self._parse_expr()
        if self._maybe("COMMA"):
            return self._parse_tuple_rest(expr)
        self._expect("RBRACE")
        return expr

    def _pminus(self) -> LeanExpr:
        self._advance()
        return LeanUnaryOp(op="-", operand=self._parse_expr(PRECEDENCE.get("MINUS", 8)))

    def _pbang(self) -> LeanExpr:
        self._advance()
        return LeanUnaryOp(op="¬", operand=self._parse_expr(PRECEDENCE.get("BANG", 11)))

    def _pdot(self) -> LeanExpr:
        self._advance()
        return LeanProj(expr=LeanHole(), field=self._expect("ID").value)

    def _phash(self) -> LeanExpr:
        self._advance()
        return self._parse_expr()

    def _plarrow(self) -> LeanExpr:
        """Handle ← (bind) as a prefix expression inside do blocks: (← expr)."""
        self._advance()  # consume ←
        return self._parse_expr()

    def _skip_expr(self) -> LeanExpr:
        """Skip an unrecognized token and return a hole placeholder."""
        self._advance()
        return LeanHole()

    def _parse_expr_by(self) -> LeanExpr:
        """Handle `by` in expression context: (by ...)."""
        self._advance()  # consume by
        return LeanBy(tactic=self._parse_tactic())

    _PREFIX_DISPATCH = {
        "ID": "_pid",
        "NUM": "_pnum",
        "FLOAT": "_pfloat",
        "STR": "_pstr",
        "CHAR": "_pchar",
        "BOOL": "_pbool",
        "WILD": "_pwild",
        "LPAREN": "_plparen",
        "LBRACK": "_plbrack",
        "LBRACE": "_plbrace",
        "FUN": "_parse_lambda",
        "FORALL": "_parse_forall",
        "MATCH": "_parse_match",
        "IF": "_parse_if",
        "LET": "_parse_let",
        "HAVE": "_parse_have",
        "SHOW": "_parse_show",
        "CALC": "_parse_calc",
        "DO": "_parse_do",
        "MINUS": "_pminus",
        "BANG": "_pbang",
        "DOT": "_pdot",
        "HASH_EVAL": "_phash",
        "HASH_CHECK": "_phash",
        "LARROW": "_plarrow",
        "BY": "_parse_expr_by",
        "BULLET": "_pwild",
        "AT": "_skip_expr",
        "HASH": "_phash",
        "BACKTICK": "_skip_expr",
        "UNION": "_skip_expr",
        "TURNSTILE": "_skip_expr",
        "TRIANGLE": "_skip_expr",
        "LANGLE": "_skip_expr",
        "RANGLE": "_skip_expr",
        "EXISTS": "_skip_expr",
        "PROD": "_skip_expr",
        "COMPOSE": "_skip_expr",
        "DIVIDES": "_skip_expr",
        "EQV": "_skip_expr",
        "BOT": "_skip_expr",
        "NOTIN": "_skip_expr",
        "SUBSET": "_skip_expr",
        "BIGUNION": "_skip_expr",
        "UPARROW": "_skip_expr",
        "SUM": "_skip_expr",
        "DOWNARROW": "_skip_expr",
        "EMPTYSET": "_skip_expr",
        "TOP": "_skip_expr",
        "BIGINF": "_skip_expr",
        "SQUNION": "_skip_expr",
        "BIGUNION2": "_skip_expr",
        "INTERSECT": "_skip_expr",
        "BACKSLASH": "_skip_expr",
        "SQCAP": "_skip_expr",
        "BIGINTER": "_skip_expr",
        "SUPMINUS": "_skip_expr",
        "INFINITY": "_skip_expr",
        "INTEGRAL": "_skip_expr",
        "PARTIAL": "_skip_expr",
        "SQRT": "_skip_expr",
        "LFLOOR": "_skip_expr",
        "CIRCLE": "_skip_expr",
        "ANGLE": "_skip_expr",
        "LCEIL": "_skip_expr",
        "SUPSET": "_skip_expr",
        "SQUARE": "_skip_expr",
        "PRIME": "_skip_expr",
        "GRADIENT": "_skip_expr",
        "NAND": "_skip_expr",
        "YEN": "_skip_expr",
        "FLAT": "_skip_expr",
        "RETURN": "_skip_expr",
        "BALLOT_X": "_skip_expr",
        "RFLOOR": "_skip_expr",
        "RCEIL": "_skip_expr",
        "DOTDOTDOT": "_skip_expr",
    }

    def _parse_prefix(self) -> LeanExpr | None:
        handler = self._PREFIX_DISPATCH.get(self._peek().kind)
        if handler is not None:
            return getattr(self, handler)()
        return None

    def _parse_struct_inst(self) -> LeanStructInst:
        name = self._advance().value
        self._expect("COLONEQ")
        fields = []
        while self._peek().kind != "RBRACE":
            fname = self._expect("ID").value
            self._expect("COLONEQ")
            fval = self._parse_expr()
            fields.append((fname, fval))
            self._maybe("COMMA")
        self._expect("RBRACE")
        return LeanStructInst(struct_name=name, fields=fields)

    def _parse_tuple_rest(self, first: LeanExpr) -> LeanTupleLit:
        elts = [first]
        elts.append(self._parse_expr())
        while self._maybe("COMMA"):
            if self._peek().kind == "RBRACE":
                break
            elts.append(self._parse_expr())
        self._expect("RBRACE")
        return LeanTupleLit(elts=elts)

    def _parse_lambda(self) -> LeanLambda:
        self._advance()
        params = []
        while self._peek().kind in ("ID", "LPAREN", "LBRACE", "WILD"):
            if self._peek().kind == "ID":
                params.append(LeanParam(name=self._advance().value, type=None))
            elif self._peek().kind == "WILD":
                self._advance()
                params.append(LeanParam(name="_", type=None))
            else:
                params.extend(self._parse_binders())
        self._expect("ARROW") if self._peek().kind == "ARROW" else self._expect(
            "RARROW"
        )
        body = self._parse_expr()
        return LeanLambda(params=params, body=body)

    def _parse_forall(self) -> LeanForall:
        self._advance()
        params = []
        while not (
            self._peek().kind in ("COMMA", "ARROW", "RARROW", "DOT")
            or (self._peek().kind == "ID" and self.tokens[self.pos + 1].kind == "COLON")
        ):
            if self._peek().kind in ("ID", "LPAREN", "LBRACE", "WILD"):
                if (
                    self._peek().kind == "ID"
                    and self.tokens[self.pos + 1].kind == "COLON"
                ):
                    name = self._advance().value
                    self._expect("COLON")
                    typ = self._parse_expr()
                    params.append(LeanParam(name=name, type=typ))
                elif self._peek().kind == "WILD":
                    self._advance()
                    params.append(LeanParam(name="_", type=None))
                elif self._peek().kind == "ID":
                    # Bare binder like `∀ n, ...` (n is the binder, type is inferred)
                    params.append(LeanParam(name=self._advance().value, type=None))
                else:
                    params.extend(self._parse_binders())
            else:
                break
        if self._peek().kind == "COMMA":
            self._advance()
        elif self._peek().kind in ("DOT", "ARROW", "RARROW"):
            self._advance()
        body = self._parse_expr()
        return LeanForall(params=params, body=body)

    def _parse_match(self) -> LeanMatch:
        self._expect("MATCH")
        expr = self._parse_expr()
        self._expect("WITH")
        if self._peek().kind == "PIPE":
            self._maybe("PIPE")
        arms = []
        while self._peek().kind in (
            "ID",
            "NUM",
            "WILD",
            "LPAREN",
            "BOOL",
            "STR",
            "CHAR",
        ) or (
            self._peek().kind == "PIPE"
            and self.tokens[self.pos + 1].kind in ("ID", "NUM", "WILD", "LPAREN")
        ):
            if self._peek().kind == "PIPE":
                self._advance()
            pat = self._parse_pattern()
            if self._peek().kind == "COLON":
                self._advance()
                pat_type = self._parse_expr()
            if self._peek().kind == "ARROW" or self._peek().value == "=>":
                self._advance()
            rhs = self._parse_expr(7)
            arms.append(LeanMatchArm(pattern=pat, rhs=rhs))
        return LeanMatch(expr=expr, arms=arms)

    def _parse_if(self) -> LeanIf:
        self._expect("IF")
        cond = self._parse_expr()
        self._expect("THEN")
        then_expr = self._parse_expr()
        else_expr = None
        if self._maybe("ELSE"):
            else_expr = self._parse_expr()
        return LeanIf(cond=cond, then_expr=then_expr, else_expr=else_expr)

    def _parse_let(self) -> LeanLet:
        self._expect("LET")
        is_rec = self._maybe("ID", "rec")
        is_mut = self._maybe("MUT") if not is_rec else False
        if self._peek().kind == "WILD":
            name = self._advance().value
        elif is_rec or self._peek().kind == "ID":
            name = self._expect("ID").value
        else:
            name = self._expect("ID").value
        params = []
        while self._peek().kind in ("LPAREN", "LBRACE", "LBRACK"):
            params.extend(self._parse_binders())
        typ = None
        if self._maybe("COLON"):
            typ = self._parse_expr()
        if self._peek().kind == "COLONEQ":
            self._advance()
        elif self._peek().value == "=":
            self._advance()
        value = self._parse_expr_until({"IN", "SEMI", "EOF"})
        if self._peek().kind == "SEMI":
            self._advance()
        else:
            self._expect("IN")
        body = self._parse_expr()
        return LeanLet(
            name=name,
            params=params,
            type=typ,
            value=value,
            body=body,
            is_mut=is_mut,
            is_rec=is_rec,
        )

    def _parse_have(self) -> LeanHave:
        self._expect("HAVE")
        name = None
        if self._peek().kind == "ID" and self.tokens[self.pos + 1].kind == "COLON":
            name = self._advance().value
            self._expect("COLON")
        typ = self._parse_expr()
        self._maybe("COLONEQ") or self._maybe("EQ") or self._maybe("ARROW")
        if self._peek().kind == "BY":
            self._advance()
            value = LeanBy(tactic=self._parse_tactic())
        else:
            value = self._parse_expr()
        if self._peek().kind in ("IN", "SEMI"):
            self._advance() if self._peek().kind == "SEMI" else self._advance()
        body = self._parse_expr()
        return LeanHave(name=name, type=typ, value=value, body=body)

    def _parse_show(self) -> LeanShow:
        self._expect("SHOW")
        typ = self._parse_expr()
        self._expect("BY")
        return LeanShow(type=typ, value=LeanBy(tactic=self._parse_tactic()))

    def _parse_calc(self) -> LeanCalc:
        self._expect("CALC")
        steps = []
        while self._peek().kind != "EOF" and self._peek().kind not in (
            "DEF",
            "THEOREM",
            "INDUCTIVE",
            "STRUCTURE",
        ):
            if self._peek().kind == "ID" or self._peek().kind in ("EQ", "LT", "GT"):
                rel = self._parse_expr()
                self._maybe("COLON") or None
                val = self._parse_expr()
                steps.append(LeanCalcStep(relation=rel, value=val))
            else:
                break
        return LeanCalc(steps=steps)

    def _parse_do(self) -> LeanDo:
        self._expect("DO")
        stmts = []
        last = None
        while self._peek().kind not in (
            "EOF",
            "DEF",
            "THEOREM",
            "INDUCTIVE",
            "STRUCTURE",
            "CLASS",
            "INSTANCE",
            "AXIOM",
        ):
            if self._peek().kind == "LET":
                self._advance()
                is_mut = self._maybe("MUT")
                name = self._expect("ID").value
                self._expect("COLONEQ")
                val = self._parse_expr()
                stmts.append(LeanDoLet(name=name, value=val, is_mut=is_mut))
            elif self._peek().kind == "ID" and self.tokens[self.pos + 1].kind in (
                "ARROW",
                "COLONEQ",
                "LARROW",
            ):
                pat = self._parse_pattern()
                arrow = self._advance()
                val = self._parse_expr()
                stmts.append(LeanDoBind(pattern=pat, value=val))
            elif self._peek().kind == "WILD" and self.tokens[self.pos + 1].kind in (
                "ARROW",
                "COLONEQ",
                "LARROW",
            ):
                pat = self._parse_pattern()
                self._advance()
                val = self._parse_expr()
                stmts.append(LeanDoBind(pattern=pat, value=val))
            else:
                last = self._parse_expr()
                break
        return LeanDo(stmts=stmts, last=last)

    # ---- Patterns ----

    def _parse_pattern(self) -> LeanPattern:
        return self._parse_pattern_or()

    def _parse_pattern_or(self) -> LeanPattern:
        left = self._parse_pattern_atom()
        if self._maybe("PIPE"):
            patterns = [left]
            patterns.append(self._parse_pattern_atom())
            while self._maybe("PIPE"):
                patterns.append(self._parse_pattern_atom())
            return LeanPatternOr(patterns=patterns)
        return left

    def _ppat_wild(self) -> LeanPattern:
        self._advance()
        return LeanPatternWild()

    def _ppat_num(self) -> LeanPattern:
        return LeanPatternNum(value=int(self._advance().value))

    def _ppat_bool(self) -> LeanPattern:
        val = self._advance().value == "true"
        return LeanPatternCtor(name="true" if val else "false", patterns=[])

    def _ppat_id(self) -> LeanPattern:
        name = self._advance().value
        if self._peek().kind == "LPAREN":
            self._advance()
            sub_patterns = []
            if self._peek().kind != "RPAREN":
                sub_patterns.append(self._parse_pattern())
                while self._maybe("COMMA"):
                    sub_patterns.append(self._parse_pattern())
            self._expect("RPAREN")
            return LeanPatternCtor(name=name, patterns=sub_patterns)
        elif self._peek().kind == "LBRACK":
            self._advance()
            sub_patterns = []
            if self._peek().kind != "RBRACK":
                sub_patterns.append(self._parse_pattern())
                while self._maybe("COMMA"):
                    sub_patterns.append(self._parse_pattern())
            self._expect("RBRACK")
            return LeanPatternCtor(name=name, patterns=sub_patterns)
        return LeanPatternIdent(name=name)

    def _ppat_lparen(self) -> LeanPattern:
        self._advance()
        if self._peek().kind == "RPAREN":
            self._advance()
            return LeanPatternCtor(name="Unit.unit", patterns=[])
        pat = self._parse_pattern()
        self._expect("RPAREN")
        return pat

    def _ppat_str(self) -> LeanPattern:
        return LeanPatternCtor(name=self._advance().value, patterns=[])

    def _ppat_char(self) -> LeanPattern:
        return LeanPatternCtor(name=self._advance().value, patterns=[])

    _PATTERN_DISPATCH = {
        "WILD": "_ppat_wild",
        "NUM": "_ppat_num",
        "BOOL": "_ppat_bool",
        "ID": "_ppat_id",
        "LPAREN": "_ppat_lparen",
        "STR": "_ppat_str",
        "CHAR": "_ppat_char",
    }

    def _parse_pattern_atom(self) -> LeanPattern:
        tok = self._peek()
        handler = self._PATTERN_DISPATCH.get(tok.kind)
        if handler is not None:
            return getattr(self, handler)()
        raise SyntaxError(f"Unexpected token in pattern: {tok}")

    # ---- Tactics ----

    _COMMAND_START_KINDS = frozenset(
        {
            "DEF",
            "THEOREM",
            "LEMMA",
            "INDUCTIVE",
            "STRUCTURE",
            "CLASS",
            "INSTANCE",
            "AXIOM",
            "OPEN",
            "NAMESPACE",
            "SECTION",
            "VARIABLE",
        }
    )

    def _is_command_start(self) -> bool:
        """Check if tokens at current position start a new command.

        Skips over @[attr] and public/private/protected modifiers
        without consuming them (restores position after check).
        """
        save = self.pos
        self._skip_attributes_and_visibility()
        tok = self._peek()
        is_cmd = tok.kind in self._COMMAND_START_KINDS or tok.value == "end"
        self.pos = save
        return is_cmd

    def _skip_tactic_body(self):
        """Consume all tokens until the next command-starting token.

        Tracks bracket depth so nested brackets inside tactics are handled.
        Stops before @[attr] that precedes a command keyword.
        """
        depth = 0
        max_iter = 10000
        iter_count = 0
        while self._peek().kind not in ("EOF",):
            if iter_count > max_iter:
                raise RuntimeError("_skip_tactic_body: max iterations exceeded")
            iter_count += 1
            if depth == 0 and self._is_command_start():
                break
            tok = self._peek()
            if tok.kind in ("LBRACK", "LPAREN", "LBRACE"):
                depth += 1
            elif tok.kind in ("RBRACK", "RPAREN", "RBRACE"):
                depth -= 1
            self._advance()

    def _parse_tactic(self) -> LeanTactic:
        self._skip_tactic_body()
        return LeanHole()
