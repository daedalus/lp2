"""Adversarial / edge-case tests for the transpiler.

These tests probe boundaries the feature tests don't hit:
empty sources, giant inputs, nesting depth, unicode, keywords
as identifiers, repeated constructs, and pathological forms.
"""

import pytest
from lp2 import py_to_lean, lean_to_py


# ── Zero / degenerate inputs ──────────────────────────────────────────

class TestEdgeEmpty:
    def test_py_empty_string(self):
        result = py_to_lean("")
        assert result is not None

    def test_py_only_whitespace(self):
        result = py_to_lean("   \n  \n  ")
        assert result is not None

    def test_py_only_comments(self):
        result = py_to_lean("# just a comment\n# another\n")
        assert result is not None

    def test_lean_empty_string(self):
        result = lean_to_py("")
        assert result is not None

    def test_lean_only_comments(self):
        result = lean_to_py("-- just a comment\n-- another\n")
        assert result is not None


# ── Python keywords used as identifiers ───────────────────────────────

class TestPyIdentKeywords:
    def test_keyword_as_param(self):
        result = py_to_lean("""def f(def_: int, class_: str) -> bool:
    return True
""")
        assert "def_" in result or "def" in result

    def test_keyword_as_var(self):
        result = py_to_lean("""def f() -> int:
    return_ = 1
    return return_
""")
        assert result


# ── Unicode identifiers (PEP 3131) ───────────────────────────────────

class TestPyUnicodeIdents:
    def test_greek_params(self):
        result = py_to_lean("""def f(α: int, β: int) -> int:
    return α + β
""")
        assert result

    def test_math_ident(self):
        result = py_to_lean("""def factorial(n: int) -> int:
    return n
""")
        assert result


# ── Large / pathological parameter lists ──────────────────────────────

class TestPyManyParams:
    def test_many_positional(self):
        args = ", ".join(f"p{i}: int" for i in range(50))
        body = "    return " + " + ".join(f"p{i}" for i in range(50))
        source = f"def f({args}) -> int:\n{body}\n"
        result = py_to_lean(source)
        assert result

    def test_very_long_func_name(self):
        name = "f" + "o" * 200
        result = py_to_lean(f"def {name}(x: int) -> int:\n    return x\n")
        assert result


# ── Deeply nested structures ──────────────────────────────────────────

class TestPyDeepNesting:
    def test_deep_nested_ifs(self):
        lines = ["def f(x: int) -> int:"]
        for i in range(50):
            kw = "if" if i == 0 else "elif"
            lines.append(f"    {kw} x == {i}:")
            lines.append(f"        return {i}")
        lines.append("    return -1")
        source = "\n".join(lines) + "\n"
        result = py_to_lean(source)
        assert result

    def test_deep_nested_expr(self):
        s = "x"
        for _ in range(30):
            s = f"(x + {s})"
        source = f"def f(x: int) -> int:\n    return {s}\n"
        result = py_to_lean(source)
        assert result

    def test_very_long_chained_bool(self):
        parts = [f"x == {i}" for i in range(40)]
        cond = " and ".join(parts)
        source = f"""def test(x: int) -> bool:
    return {cond}
"""
        result = py_to_lean(source)
        assert result


# ── Numeric edge-cases ────────────────────────────────────────────────

class TestPyNumeric:
    def test_large_int(self):
        large = 10 ** 50
        source = f"def f() -> int:\n    return {large}\n"
        result = py_to_lean(source)
        assert str(large) in result

    def test_negative_int(self):
        result = py_to_lean("def f() -> int:\n    return -42\n")
        assert "-42" in result or "42" in result

    def test_float(self):
        result = py_to_lean("def f() -> float:\n    return 3.14\n")
        assert "3.14" in result or "3_14" in result

    def test_sci_notation(self):
        result = py_to_lean("def f() -> float:\n    return 1.5e10\n")
        assert result


# ── String edge-cases ─────────────────────────────────────────────────

class TestPyString:
    def test_empty_string(self):
        result = py_to_lean("""def f() -> str:
    return ""
""")
        assert result

    def test_escaped_string(self):
        result = py_to_lean("""def f() -> str:
    return "hello\\nworld\\ttab"
""")
        assert result

    def test_unicode_string(self):
        result = py_to_lean("""def f() -> str:
    return "héllo wörld ∀"
""")
        assert result


# ── Many statements / repetitive bodies ───────────────────────────────

class TestPyRepetition:
    def test_many_returns(self):
        source = "def f(x: int) -> int:\n"
        for i in range(30):
            source += f"    if x == {i}: return {i}\n"
        source += "    return -1\n"
        result = py_to_lean(source)
        assert result


# ── Zero-argument / degenerate functions ──────────────────────────────

class TestPyDegenerate:
    def test_no_params_no_body(self):
        result = py_to_lean("def f() -> None:\n    pass\n")
        assert result

    def test_only_pass(self):
        result = py_to_lean("def f() -> None:\n    pass\n")
        assert result

    def test_only_return_literal(self):
        result = py_to_lean("def f() -> int:\n    return 1\n")
        assert "1" in result


# ── Lean adversary tests ──────────────────────────────────────────────

class TestLeanIdentKeywords:
    def test_keyword_as_ident(self):
        with pytest.raises(SyntaxError):
            lean_to_py("def if (x : Int) : Int := x\n")


class TestLeanUnicodeIdents:
    def test_unicode_ident(self):
        result = lean_to_py("def α (β : Int) : Int := β\n")
        assert result


class TestLeanDeepNesting:
    def test_deep_app(self):
        src = "def f (x : Int) : Int := " + "".join(f"g{i} (" for i in range(30)) + "x" + ")" * 30 + "\n"
        result = lean_to_py(src)
        assert result

    def test_deep_binop(self):
        s = "x"
        for _ in range(20):
            s = f"x + ({s})"
        source = f"def f (x : Int) : Int := {s}\n"
        result = lean_to_py(source)
        assert result


class TestLeanNumeric:
    def test_large_int(self):
        source = f"def f : Int := {10**40}\n"
        result = lean_to_py(source)
        assert result

    def test_float(self):
        result = lean_to_py("def f : Float := 3.14\n")
        assert result


class TestLeanDegenerate:
    def test_no_body(self):
        result = lean_to_py("def f : Int := 0\n")
        assert result

    def test_unit_return(self):
        result = lean_to_py("def f : Unit := ()\n")
        assert result

    def test_sort(self):
        result = lean_to_py("def f : Type := Type\n")
        assert result


# ── Round-trip irregular forms ────────────────────────────────────────

class TestRoundTripAdversary:
    def test_deep_nested_rt(self):
        source = "def f(x: int) -> int:\n    return " + "(" * 30 + "x + 1" + ")" * 30 + "\n"
        middle = py_to_lean(source)
        result = lean_to_py(middle)
        assert "x + 1" in result or "x+1" in result

    def test_strings_rt(self):
        source = 'def f() -> str:\n    return "hello world"\n'
        middle = py_to_lean(source)
        result = lean_to_py(middle)
        assert "hello" in result

    def test_bool_negation_rt(self):
        source = "def f(b: bool) -> bool:\n    return not b\n"
        middle = py_to_lean(source)
        result = lean_to_py(middle)
        assert result


# ── Property-style tests ──────────────────────────────────────────────

class TestPropertySurvival:
    """Ensure the transpiler never crashes on well-formed inputs."""

    PY_SNIPPETS = [
        "def f(x: int) -> int:\n    return -x\n",
        "def f(x: int, y: int) -> int:\n    return x - y\n",
        "def f(x: int) -> int:\n    return x // 2\n",
        "def f(x: int) -> int:\n    return x % 3\n",
        "def f(x: int) -> int:\n    return x ** 2\n",
        "def f(x: int, y: int) -> bool:\n    return x is y\n",
        "def f(x: int, y: int) -> bool:\n    return x is not y\n",
        "def f(x: int) -> bool:\n    return x == 1 == 2\n",
        "def f() -> list:\n    return [x for x in [1,2,3]]\n",
        "def f(x: int) -> int:\n    return x if x > 0 else 0\n",
    ]

    @pytest.mark.parametrize("code", PY_SNIPPETS)
    def test_py_survives(self, code):
        result = py_to_lean(code)
        assert result

    LEAN_SNIPPETS = [
        "def f (x : Int) : Int := -x\n",
        "def f (x : Int) : Int := x - y\n",
        "def f (x : Int) : Int := x / 2\n",
        "def f (x : Int) : Int := x % 3\n",
        "def f : List Int := []\n",
        "def f : List Int := [1]\n",
        "def f : Nat := 0\n",
        "def f : Nat := 1\n",
        "def f (x : Int) : Int := if x > 0 then x else -x\n",
    ]

    @pytest.mark.parametrize("code", LEAN_SNIPPETS)
    def test_lean_survives(self, code):
        result = lean_to_py(code)
        assert result
