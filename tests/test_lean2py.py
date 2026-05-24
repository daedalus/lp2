"""Tests for Lean4 → Python translation."""

import pytest
from lp2 import lean_to_py


class TestLeanToPyBasic:
    def test_simple_def(self):
        result = lean_to_py("def add (x y : Int) : Int := x + y\n")
        assert "def add(x: int, y: int) -> int:" in result
        assert "return x + y" in result

    def test_no_annotation(self):
        result = lean_to_py("def f x := x\n")
        assert "def f(" in result

    def test_if_then_else(self):
        result = lean_to_py("def max (a b : Int) : Int := if a >= b then a else b\n")
        assert "if" in result
        assert "else" in result

    def test_recursion(self):
        result = lean_to_py(
            "def fact (n : Int) : Int := if n <= 1 then 1 else n * fact (n - 1)\n"
        )
        assert "fact(n - 1)" in result or "fact (n - 1)" in result

    def test_match(self):
        result = lean_to_py(
            "def isZero (n : Int) : Bool := match n with | 0 => true | _ => false\n"
        )
        assert "match" in result
        assert "case" in result


class TestLeanToPyOperators:
    def test_binop(self):
        result = lean_to_py("def f (x y : Int) : Int := x + y * 2\n")
        assert "x + y * 2" in result or "y * 2" in result

    def test_unicode_comparison(self):
        result = lean_to_py("def le (a b : Int) : Bool := a ≤ b\n")
        assert "<=" in result

    def test_unicode_neq(self):
        result = lean_to_py("def ne (a b : Int) : Bool := a ≠ b\n")
        assert "!=" in result


class TestLeanToPyEdgeCases:
    def test_no_return_type(self):
        result = lean_to_py("def f x := x + 1\n")
        assert result

    def test_multi_param_def(self):
        result = lean_to_py("def f (a b c : Int) : Int := a + b + c\n")
        assert "f(a: int, b: int, c: int)" in result

    def test_single_expr_body(self):
        result = lean_to_py("def answer : Int := 42\n")
        assert "42" in result

    def test_empty_params(self):
        result = lean_to_py("def f : Int := 1\n")
        assert result


class TestLeanToPyErrors:
    def test_invalid_syntax(self):
        with pytest.raises(SyntaxError):
            lean_to_py("def !!!\n")
