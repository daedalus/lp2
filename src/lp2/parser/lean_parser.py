from __future__ import annotations
from typing import Optional
from lp2.ast.lean4_ast import *
from lp2.parser.lean_lexer import LeanLexer, Token


PRECEDENCE = {
    "RARROW": 1,
    "COLON": 2,
    "PIPEOP": 3,
    "EQ": 4,
    "DEQ": 4,
    "LT": 4,
    "GT": 4,
    "LE": 4,
    "GE": 4,
    "NE": 4,
    "AMP": 5,
    "PIPE": 6,
    "DOUBLECOLON": 7,
    "PLUS": 8,
    "MINUS": 8,
    "STAR": 9,
    "SLASH": 9,
    "PERCENT": 9,
    "HAT": 10,
    "BANG": 11,
}


PREFIX_KW = {"FUN", "FORALL", "MATCH", "IF", "LET", "HAVE", "SHOW", "CALC", "DO"}
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
    "PIPE": "||",
    "HAT": "^",
    "RARROW": "→",
    "PIPEOP": "|>",
}


class LeanParser:
    def __init__(self, source: str):
        self.lexer = LeanLexer(source)
        self.tokens = self.lexer.tokens
        self.pos = 0

    def _peek(self, offset: int = 0) -> Token:
        return self.tokens[self.pos + offset]

    def _advance(self) -> Token:
        t = self.tokens[self.pos]
        self.pos += 1
        return t

    def _expect(self, kind: str, value: Optional[str] = None) -> Token:
        t = self._peek()
        if t.kind != kind or (value is not None and t.value != value):
            raise SyntaxError(
                f"Expected {kind}({value}), got {t.kind}({t.value}) at line {t.line}, col {t.col}"
            )
        return self._advance()

    def _maybe(self, kind: str, value: Optional[str] = None) -> bool:
        t = self._peek()
        if t.kind == kind and (value is None or t.value == value):
            self._advance()
            return True
        return False

    def _skip_to(self, kinds: set[str]):
        while self._peek().kind not in kinds and self._peek().kind != "EOF":
            self._advance()

    # ---- Top Level ----

    def parse_module(self) -> LeanModule:
        imports = []
        body = []
        while self._peek().kind != "EOF":
            if self._peek().kind == "OPEN":
                open_cmd = self._parse_open()
                body.append(open_cmd)
            elif self._peek().kind in ("DEF", "THEOREM", "LEMMA"):
                body.append(self._parse_def())
            elif self._peek().kind == "INDUCTIVE":
                body.append(self._parse_inductive())
            elif self._peek().kind == "STRUCTURE":
                body.append(self._parse_structure())
            elif self._peek().kind == "CLASS":
                body.append(self._parse_class())
            elif self._peek().kind == "INSTANCE":
                body.append(self._parse_instance())
            elif self._peek().kind == "AXIOM":
                body.append(self._parse_axiom())
            elif self._peek().kind == "EXAMPLE":
                body.append(self._parse_example())
            elif self._peek().kind == "NAMESPACE":
                body.append(self._parse_namespace())
            elif self._peek().kind == "SECTION":
                body.append(self._parse_section())
            elif self._peek().kind == "VARIABLE":
                body.append(self._parse_variable())
            elif self._peek().kind == "HASH_EVAL" or self._peek().kind == "HASH_CHECK":
                self._advance()
                body.append(LeanExample(expr=self._parse_expr()))
            else:
                try:
                    body.append(self._parse_def())
                except SyntaxError:
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
        self._expect("DEF")
        name_token = self._expect("ID")
        name = name_token.value

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
        while self._peek().kind == "DEF" or (
            self._peek().kind == "ID" and self._peek().value != "end"
        ):
            methods.append(self._parse_def())
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
        while self._peek().kind not in ("EOF",) and self._peek().value != "end":
            commands.append(
                self._parse_def()
                if self._peek().kind == "DEF"
                else self._parse_inductive()
                if self._peek().kind == "INDUCTIVE"
                else self._parse_namespace()
            )
        if self._peek().value == "end":
            self._advance()
        return LeanNamespace(name=name, commands=commands)

    def _parse_section(self) -> LeanSection:
        self._expect("SECTION")
        params = []
        while self._peek().kind in ("LPAREN", "LBRACE", "LBRACK"):
            params.extend(self._parse_binders())
        commands = []
        while self._peek().kind not in ("EOF",) and self._peek().value != "end":
            try:
                commands.append(self._parse_def())
            except SyntaxError:
                break
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

    def _parse_expr(self, min_prec: int = 0) -> LeanExpr:
        lhs = self._parse_prefix()
        if lhs is None:
            t = self._peek()
            raise SyntaxError(
                f"Unexpected token {t.kind}({t.value}) at line {t.line}, col {t.col}"
            )

        while True:
            tok = self._peek()
            if tok.kind in BINARY_OPS and PRECEDENCE.get(tok.kind, 0) >= min_prec:
                prec = PRECEDENCE[tok.kind]
                op = BINARY_OPS[tok.kind]
                self._advance()
                if op == "→" and tok.kind == "RARROW":
                    rhs = self._parse_expr(prec)
                    lhs = LeanTypeArrow(from_type=lhs, to_type=rhs)
                elif op == ":":
                    rhs = self._parse_expr(prec)
                    lhs = LeanTypeSpec(expr=lhs, type=rhs)
                elif op in ("=", "<", ">", "::", "&&", "||", "|>"):
                    rhs = self._parse_expr(prec)
                    lhs = LeanBinOp(left=lhs, op=op, right=rhs)
                else:
                    rhs = self._parse_expr(prec)
                    lhs = LeanBinOp(left=lhs, op=op, right=rhs)
            elif tok.kind == "DOT":
                self._advance()
                field = self._expect("ID").value
                lhs = LeanProj(expr=lhs, field=field)
            elif (
                tok.kind == "ID"
                or tok.kind == "NUM"
                or tok.kind == "STR"
                or tok.kind == "BOOL"
                or tok.kind == "FLOAT"
                or tok.kind == "CHAR"
                or tok.kind == "LPAREN"
                or tok.kind == "LBRACK"
                or tok.kind == "LBRACE"
                or tok.kind == "WILD"
            ):
                if PRECEDENCE.get("APP", 13) >= min_prec:
                    lhs = LeanApp(func=lhs, arg=self._parse_prefix())
                else:
                    break
            elif tok.kind == "DOT" and self._peek(1) and self._peek(2):
                pass
            else:
                break

        return lhs

    def _parse_prefix(self) -> Optional[LeanExpr]:
        tok = self._peek()

        if tok.kind == "ID":
            return LeanIdent(name=self._advance().value)
        elif tok.kind == "NUM":
            n_val = int(self._advance().value)
            return LeanNum(value=n_val, is_nat=n_val >= 0)
        elif tok.kind == "FLOAT":
            f_val = float(self._advance().value)
            return LeanFloat(value=f_val)
        elif tok.kind == "STR":
            return LeanString(value=self._advance().value)
        elif tok.kind == "CHAR":
            return LeanChar(value=self._advance().value)
        elif tok.kind == "BOOL":
            v = self._advance().value == "true"
            return LeanBool(value=v)
        elif tok.kind == "WILD":
            self._advance()
            return LeanHole()
        elif tok.kind == "LPAREN":
            self._advance()
            if self._peek().kind == "RPAREN":
                self._advance()
                return LeanUnit()
            if self._maybe("COLON"):
                typ = self._parse_expr()
                if self._maybe("RPAREN"):
                    return LeanTypeSpec(expr=LeanHole(), type=typ)
                self._expect("RPAREN")
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
        elif tok.kind == "LBRACK":
            self._advance()
            elts = []
            if self._peek().kind != "RBRACK":
                elts.append(self._parse_expr())
                while self._maybe("COMMA"):
                    elts.append(self._parse_expr())
            self._expect("RBRACK")
            return LeanListLit(elts=elts)
        elif tok.kind == "LBRACE":
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
        elif tok.kind == "FUN":
            return self._parse_lambda()
        elif tok.kind == "FORALL":
            return self._parse_forall()
        elif tok.kind == "MATCH":
            return self._parse_match()
        elif tok.kind == "IF":
            return self._parse_if()
        elif tok.kind == "LET":
            return self._parse_let()
        elif tok.kind == "HAVE":
            return self._parse_have()
        elif tok.kind == "SHOW":
            return self._parse_show()
        elif tok.kind == "CALC":
            return self._parse_calc()
        elif tok.kind == "DO":
            return self._parse_do()
        elif tok.kind == "MINUS":
            self._advance()
            return LeanUnaryOp(
                op="-", operand=self._parse_expr(PRECEDENCE.get("MINUS", 8))
            )
        elif tok.kind == "BANG":
            self._advance()
            return LeanUnaryOp(
                op="¬", operand=self._parse_expr(PRECEDENCE.get("BANG", 11))
            )
        elif tok.kind == "DOT":
            self._advance()
            field = self._expect("ID").value
            return LeanProj(expr=LeanHole(), field=field)
        elif tok.kind == "HASH_EVAL" or tok.kind == "HASH_CHECK":
            self._advance()
            return self._parse_expr()
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
        is_mut = self._maybe("MUT")
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
        value = self._parse_expr()
        self._expect("IN")
        body = self._parse_expr()
        return LeanLet(
            name=name, params=params, type=typ, value=value, body=body, is_mut=is_mut
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
            ):
                pat = self._parse_pattern()
                arrow = self._advance()
                val = self._parse_expr()
                stmts.append(LeanDoBind(pattern=pat, value=val))
            elif self._peek().kind == "WILD" and self.tokens[self.pos + 1].kind in (
                "ARROW",
                "COLONEQ",
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

    def _parse_pattern_atom(self) -> LeanPattern:
        tok = self._peek()
        if tok.kind == "WILD":
            self._advance()
            return LeanPatternWild()
        elif tok.kind == "NUM":
            return LeanPatternNum(value=int(self._advance().value))
        elif tok.kind == "BOOL":
            val = self._advance().value == "true"
            return LeanPatternCtor(name="true" if val else "false", patterns=[])
        elif tok.kind == "ID":
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
        elif tok.kind == "LPAREN":
            self._advance()
            if self._peek().kind == "RPAREN":
                self._advance()
                return LeanPatternCtor(name="Unit.unit", patterns=[])
            pat = self._parse_pattern()
            self._expect("RPAREN")
            return pat
        elif tok.kind == "STR":
            return LeanPatternCtor(name=self._advance().value, patterns=[])
        elif tok.kind == "CHAR":
            return LeanPatternCtor(name=self._advance().value, patterns=[])
        raise SyntaxError(f"Unexpected token in pattern: {tok}")

    # ---- Tactics ----

    def _parse_tactic(self) -> LeanTactic:
        return LeanHole()
