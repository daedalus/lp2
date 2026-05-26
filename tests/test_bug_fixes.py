"""Regression tests for all bugs fixed in the review."""

from lp2 import lean_to_py, py_to_lean
from lp2.codegen.python_codegen import generate_python
from lp2.parser.lean_lexer import LeanLexer
from lp2.parser.python_parser import parse_python

# ---------------------------------------------------------------------------
# python_parser.py — bare raise
# ---------------------------------------------------------------------------


class TestBareRaise:
    def test_bare_raise_does_not_crash(self):
        """Bare ``raise`` (re-raise) must not crash with AttributeError."""
        src = "def f():\n    try:\n        pass\n    except Exception:\n        raise\n"
        result = py_to_lean(src)
        assert result  # smoke-test: should not raise

    def test_raise_with_exception_still_works(self):
        src = "def f():\n    raise ValueError('oops')\n"
        result = py_to_lean(src)
        assert result


# ---------------------------------------------------------------------------
# python_parser.py / python_ast.py — PyMatchOr round-trip
# ---------------------------------------------------------------------------


class TestMatchOr:
    def test_match_or_preserved(self):
        """OR patterns must not silently drop alternatives."""
        src = (
            "def classify(x: int) -> str:\n"
            "    match x:\n"
            "        case 0 | 1:\n"
            "            return 'small'\n"
            "        case _:\n"
            "            return 'big'\n"
        )
        # Parse to AST — should not crash and PyMatchOr must appear
        module = parse_python(src)
        match_stmt = module.body[0].body[0]  # first function → first stmt = match
        first_case = match_stmt.cases[0]
        from lp2.ast.python_ast import PyMatchOr

        assert isinstance(first_case.pattern, PyMatchOr), (
            f"Expected PyMatchOr, got {type(first_case.pattern).__name__}"
        )
        assert len(first_case.pattern.patterns) == 2

    def test_match_or_codegen(self):
        """Codegen for PyMatchOr must emit ``case 0 | 1:`` syntax."""
        src = (
            "def f(x: int) -> str:\n"
            "    match x:\n"
            "        case 0 | 1:\n"
            "            return 'yes'\n"
            "        case _:\n"
            "            return 'no'\n"
        )
        module = parse_python(src)
        code = generate_python(module)
        assert "0 | 1" in code

    def test_lean_match_or_roundtrip(self):
        """OR pattern must survive Python→Lean→Python round-trip."""
        from lp2.ast.python_ast import PyImport as PyImportNode

        src = (
            "def f(x: int) -> str:\n"
            "    match x:\n"
            "        case 0 | 1:\n"
            "            return 'yes'\n"
            "        case _:\n"
            "            return 'no'\n"
        )
        lean = py_to_lean(src)
        assert lean
        py_result = lean_to_py(lean)
        module = parse_python(py_result)
        # Skip any leading import statements
        idx = 0
        while idx < len(module.body) and isinstance(module.body[idx], PyImportNode):
            idx += 1
        match_stmt = module.body[idx].body[0]
        first_case = match_stmt.cases[0]
        from lp2.ast.python_ast import PyMatchOr

        assert isinstance(first_case.pattern, PyMatchOr), (
            f"Expected PyMatchOr after round-trip, got {type(first_case.pattern).__name__}"
        )
        assert len(first_case.pattern.patterns) == 2


# ---------------------------------------------------------------------------
# lean_lexer.py — exponential notation without decimal point
# ---------------------------------------------------------------------------


class TestExponentialLexing:
    def test_1e10_lexes_as_float(self):
        """``1e10`` must produce a single FLOAT token, not NUM + ID."""
        tokens = LeanLexer("1e10").tokens
        kinds = [t.kind for t in tokens if t.kind != "EOF"]
        assert kinds == ["FLOAT"], f"Got token kinds: {kinds}"

    def test_1E5_lexes_as_float(self):
        tokens = LeanLexer("1E5").tokens
        kinds = [t.kind for t in tokens if t.kind != "EOF"]
        assert kinds == ["FLOAT"], f"Got token kinds: {kinds}"

    def test_1e_minus_3_lexes_as_float(self):
        tokens = LeanLexer("1e-3").tokens
        kinds = [t.kind for t in tokens if t.kind != "EOF"]
        assert kinds == ["FLOAT"], f"Got token kinds: {kinds}"

    def test_1_dot_5e2_lexes_as_float(self):
        """Existing decimal-then-exponent path must still work."""
        tokens = LeanLexer("1.5e2").tokens
        kinds = [t.kind for t in tokens if t.kind != "EOF"]
        assert kinds == ["FLOAT"], f"Got token kinds: {kinds}"


# ---------------------------------------------------------------------------
# lean_lexer.py + lean_parser.py — semicolon in let expression
# ---------------------------------------------------------------------------


class TestLetSemicolon:
    def test_lean_parser_accepts_semicolon_let(self):
        """Parser must accept ``let x := v; body`` (Lean 4 form)."""
        result = lean_to_py("def f (x : Int) : Int := let y := x + 1; y * 2\n")
        assert result

    def test_lean_parser_still_accepts_in_let(self):
        """Parser must still accept ``let x := v in body`` (backwards compat)."""
        result = lean_to_py("def f (x : Int) : Int := let y := x + 1 in y * 2\n")
        assert result


# ---------------------------------------------------------------------------
# lean4_codegen.py — let uses semicolon (Lean 4 form)
# ---------------------------------------------------------------------------


class TestLetCodegen:
    def test_let_codegen_emits_semicolon(self):
        """Lean codegen must emit ``;`` after let value, not ``in``."""
        result = py_to_lean("def f(x: int) -> int:\n    y = x + 1\n    return y * 2\n")
        # The let binding must use ";" not " in "
        if "let y" in result:
            assert " in " not in result, f"Found Lean 3 'in' syntax: {result}"
            assert ";" in result


# ---------------------------------------------------------------------------
# python_to_lean4.py — list literal round-trip (was: broken f-string tail)
# ---------------------------------------------------------------------------


class TestListLiteralTranspile:
    def test_list_literal_does_not_produce_object_repr(self):
        """List literal must not contain ``LeanNum(`` or ``.self`` in output."""
        result = py_to_lean("def f() -> list:\n    return [1, 2, 3]\n")
        assert "LeanNum" not in result
        assert ".self" not in result

    def test_list_cons_nil_structure(self):
        """List literal must be constructed via nested List.cons ... List.nil."""
        result = py_to_lean("def f() -> list:\n    return [1, 2]\n")
        cons_indices = []
        start = 0
        while True:
            idx = result.find("List.cons", start)
            if idx == -1:
                break
            cons_indices.append(idx)
            start = idx + len("List.cons")

        nil_idx = result.find("List.nil")

        assert len(cons_indices) >= 2, (
            f"Expected multiple List.cons applications in:\n{result}"
        )
        assert nil_idx != -1, f"Expected List.nil terminator in:\n{result}"
        assert all(idx < nil_idx for idx in cons_indices), (
            f"Expected all List.cons before List.nil in:\n{result}"
        )

        round_tripped = lean_to_py(result)
        assert round_tripped.count("List.cons") >= 2, (
            f"Expected multiple List.cons in round-trip, got:\n{round_tripped}"
        )
        assert "nil" in round_tripped, (
            f"Expected nil terminator in round-trip, got:\n{round_tripped}"
        )


# ---------------------------------------------------------------------------
# lean4_codegen.py — BinOp parenthesisation
# ---------------------------------------------------------------------------


class TestLeanBinOpParens:
    def test_left_assoc_no_extra_parens(self):
        """``a + b + c`` must not become ``(a + b) + c``."""
        result = py_to_lean(
            "def f(a: int, b: int, c: int) -> int:\n    return a + b + c\n"
        )
        assert "a + b + c" in result, f"Unexpected output: {result}"

    def test_mul_over_add_parenthesised(self):
        """``(a + b) * c`` must keep parens for precedence correctness."""
        result = py_to_lean(
            "def f(a: int, b: int, c: int) -> int:\n    return (a + b) * c\n"
        )
        assert "(a + b) * c" in result, f"Unexpected output: {result}"


# ---------------------------------------------------------------------------
# python_codegen.py — not operator spacing
# ---------------------------------------------------------------------------


class TestNotOperatorSpacing:
    def test_not_has_space(self):
        """``not b`` must emit ``not b``, not ``notb``."""
        from lp2.ast.python_ast import (
            PyFunctionDef,
            PyModule,
            PyName,
            PyReturn,
            PyUnaryOp,
        )

        module = PyModule(
            body=[
                PyFunctionDef(
                    name="f",
                    args=[("b", None, None)],
                    return_type=None,
                    body=[PyReturn(value=PyUnaryOp(op="not", operand=PyName(id="b")))],
                )
            ]
        )
        code = generate_python(module)
        assert "not b" in code, f"Expected 'not b', got: {code}"
        assert "notb" not in code

    def test_negation_no_space(self):
        """Unary ``-`` must emit ``-x``, not ``- x``."""
        from lp2.ast.python_ast import (
            PyFunctionDef,
            PyModule,
            PyName,
            PyReturn,
            PyUnaryOp,
        )

        module = PyModule(
            body=[
                PyFunctionDef(
                    name="f",
                    args=[("x", None, None)],
                    return_type=None,
                    body=[PyReturn(value=PyUnaryOp(op="-", operand=PyName(id="x")))],
                )
            ]
        )
        code = generate_python(module)
        assert "-x" in code


# ---------------------------------------------------------------------------
# python_codegen.py — match guard syntax
# ---------------------------------------------------------------------------


class TestMatchGuardSyntax:
    def test_guard_on_case_line(self):
        """Guards must be emitted as ``case pat if guard:`` on one line."""
        src = (
            "def f(x: int) -> str:\n"
            "    match x:\n"
            "        case n if n > 0:\n"
            "            return 'pos'\n"
            "        case _:\n"
            "            return 'other'\n"
        )
        module = parse_python(src)
        code = generate_python(module)
        # Guard must appear on the case line
        for line in code.splitlines():
            if "case n" in line:
                assert "if n > 0" in line, f"Guard not on case line: {line!r}"

    def test_guard_indentation_correct(self):
        """Case body must be indented at the same level (not extra-deep)."""
        src = (
            "def f(x: int) -> int:\n"
            "    match x:\n"
            "        case n if n > 0:\n"
            "            return n\n"
            "        case _:\n"
            "            return 0\n"
        )
        module = parse_python(src)
        code = generate_python(module)
        # 'return n' must appear, indented at 8 spaces (match body)
        lines = [l for l in code.splitlines() if "return n" in l]
        assert lines, "return n not found in output"
        assert lines[0].startswith(" " * 8), f"Wrong indentation: {lines[0]!r}"


# ---------------------------------------------------------------------------
# python_codegen.py — BinOp parenthesisation
# ---------------------------------------------------------------------------


class TestPyBinOpParens:
    def test_left_assoc_no_extra_parens(self):
        """``a + b + c`` must remain ``a + b + c``."""
        from lp2.ast.python_ast import (
            PyBinOp,
            PyFunctionDef,
            PyModule,
            PyName,
            PyReturn,
        )

        expr = PyBinOp(
            left=PyBinOp(left=PyName("a"), op="+", right=PyName("b")),
            op="+",
            right=PyName("c"),
        )
        module = PyModule(body=[PyFunctionDef("f", [], None, [PyReturn(value=expr)])])
        code = generate_python(module)
        assert "a + b + c" in code

    def test_mul_over_add_parenthesised(self):
        """``(a + b) * c`` must preserve parens."""
        from lp2.ast.python_ast import (
            PyBinOp,
            PyFunctionDef,
            PyModule,
            PyName,
            PyReturn,
        )

        expr = PyBinOp(
            left=PyBinOp(left=PyName("a"), op="+", right=PyName("b")),
            op="*",
            right=PyName("c"),
        )
        module = PyModule(body=[PyFunctionDef("f", [], None, [PyReturn(value=expr)])])
        code = generate_python(module)
        assert "(a + b) * c" in code


# ---------------------------------------------------------------------------
# lean4_to_python.py — LeanMatch as sub-expression
# ---------------------------------------------------------------------------


class TestLeanMatchSubExpr:
    def test_match_subexpr_is_valid_python(self):
        """A LeanMatch appearing as a sub-expression must produce valid Python."""
        from lp2.ast.lean4_ast import (
            LeanBool,
            LeanIdent,
            LeanMatch,
            LeanMatchArm,
            LeanPatternNum,
            LeanPatternWild,
        )
        from lp2.transpiler.lean4_to_python import _expr_to_py

        match_node = LeanMatch(
            expr=LeanIdent("n"),
            arms=[
                LeanMatchArm(pattern=LeanPatternNum(0), rhs=LeanBool(True)),
                LeanMatchArm(pattern=LeanPatternWild(), rhs=LeanBool(False)),
            ],
        )
        result = _expr_to_py(match_node)
        from lp2.ast.python_ast import (
            PyCall,
            PyFunctionDef,
            PyIfExp,
            PyModule,
            PyName,
            PyReturn,
        )

        assert not (
            isinstance(result, PyCall)
            and isinstance(result.func, PyName)
            and result.func.id == "match"
        ), "LeanMatch as sub-expr still produces invalid PyCall to 'match'"
        # Must be a ternary chain: PyIfExp(test, body, orelse)
        assert isinstance(result, PyIfExp), (
            f"Expected PyIfExp chain, got {type(result).__name__}"
        )
        code = generate_python(
            PyModule(
                body=[
                    PyFunctionDef(
                        name="g",
                        args=[("n", PyName("int"), None)],
                        return_type=PyName("bool"),
                        body=[PyReturn(value=result)],
                    )
                ]
            )
        )
        ns: dict = {}
        exec(compile(code, "<test>", "exec"), ns)
        assert ns["g"](0) is True
        assert ns["g"](1) is False


# ---------------------------------------------------------------------------
# lean4_codegen.py — dead branch in _gen_params removed (smoke test)
# ---------------------------------------------------------------------------


class TestGenParams:
    def test_many_params(self):
        """Functions with >2 params must format correctly."""
        result = py_to_lean(
            "def f(a: int, b: int, c: int) -> int:\n    return a + b + c\n"
        )
        assert "a" in result
        assert "b" in result
        assert "c" in result
