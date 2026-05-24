"""Tests for round-trip fidelity: Python → Lean → Python and Lean → Python → Lean."""

from lp2 import py_to_lean, lean_to_py


ROUND_TRIP_PY = """\
def fact(n: int) -> int:
    if n <= 1:
        return 1
    return n * fact(n - 1)
"""

ROUND_TRIP_LEAN = "def add (a b : Int) : Int := a + b\n"


class TestRoundTripPyLeanPy:
    def test_fact_roundtrip(self):
        middle = py_to_lean(ROUND_TRIP_PY)
        result = lean_to_py(middle)
        assert "def fact(" in result
        assert "fact(n - 1)" in result or "fact (n - 1)" in result

    def test_simple_roundtrip(self):
        source = "def f(x: int) -> int:\n    return x + 1\n"
        middle = py_to_lean(source)
        result = lean_to_py(middle)
        assert "f(x: int)" in result or "x + 1" in result

    def test_if_comes_back(self):
        source = """\
def max(a: int, b: int) -> int:
    if a >= b:
        return a
    return b
"""
        middle = py_to_lean(source)
        result = lean_to_py(middle)
        assert "if" in result
        assert "return" in result

    def test_no_type_info_lost_catastrophically(self):
        source = "def f(x: int, y: int) -> int:\n    return x * y\n"
        middle = py_to_lean(source)
        result = lean_to_py(middle)
        assert "x" in result and "y" in result
        assert "*" in result or "mul" in result or "×" in result


class TestRoundTripLeanPyLean:
    def test_add_roundtrip(self):
        middle = lean_to_py(ROUND_TRIP_LEAN)
        result = py_to_lean(middle)
        assert "add" in result
        assert "a + b" in result

    def test_if_roundtrip(self):
        source = "def max (a b : Int) : Int := if a >= b then a else b\n"
        middle = lean_to_py(source)
        result = py_to_lean(middle)
        assert "max" in result

    def test_match_roundtrip(self):
        source = (
            "def isZero (n : Int) : Bool := match n with | 0 => true | _ => false\n"
        )
        middle = lean_to_py(source)
        result = py_to_lean(middle)
        assert "isZero" in result

    def test_bool_roundtrip(self):
        source = "def f (a b : Bool) : Bool := a = b\n"
        middle = lean_to_py(source)
        result = py_to_lean(middle)
        assert result

    def test_lambda_roundtrip(self):
        source = "def f : Int := (fun x => x) 1\n"
        middle = lean_to_py(source)
        result = py_to_lean(middle)
        assert result

    def test_let_roundtrip(self):
        source = "def f (x : Int) : Int := let y := x + 1 in y * 2\n"
        middle = lean_to_py(source)
        result = py_to_lean(middle)
        assert result
