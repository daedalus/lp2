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


class TestLeanToPyStructures:
    def test_simple_structure(self):
        result = lean_to_py("structure Point where\n  x : Int\n  y : Int\n")
        assert "class Point" in result

    def test_inductive(self):
        result = lean_to_py("inductive Bool2 where\n  | true : Bool2\n  | false : Bool2\n")
        assert "class Bool2" in result


class TestLeanToPyExpressions:
    def test_lambda(self):
        result = lean_to_py("def f : Int := (fun x => x + 1) 2\n")
        assert result

    def test_let_expr(self):
        result = lean_to_py("def f (x : Int) : Int := let y := x + 1 in y * 2\n")
        assert result

    def test_projection(self):
        result = lean_to_py("def f (p : Point) : Int := p.x\n")
        assert result

    def test_type_spec(self):
        result = lean_to_py("def f (x : Nat) : Nat := (x : Nat) + 1\n")
        assert result

    def test_hole(self):
        result = lean_to_py("def f : Nat := _\n")
        assert "_" in result

    def test_list_lit(self):
        result = lean_to_py("def f : List Nat := [1, 2, 3]\n")
        assert result

    def test_tuple_lit(self):
        result = lean_to_py("def f : Prod Nat Nat := (1, 2)\n")
        assert result


class TestLeanToPyTypeAnnotations:
    def test_list_type(self):
        result = lean_to_py("def f (xs : List Int) : Int := 1\n")
        assert "list[int]" in result.lower() or "list" in result

    def test_option_type(self):
        result = lean_to_py("def f (x : Option Int) : Int := 1\n")
        assert "optional[int]" in result.lower() or "option" in result.lower()


class TestLeanToPyEdgeCases:
    def test_invalid_syntax(self):
        with pytest.raises(SyntaxError):
            lean_to_py("def !!!\n")
