"""Tests for Python → Lean4 translation."""

import pytest
from lp2 import py_to_lean


class TestPyToLeanBasic:
    def test_simple_function(self):
        result = py_to_lean("def f(x: int) -> int:\n    return x + 1\n")
        assert "def f (x : Int) : Int" in result
        assert "x + 1" in result

    def test_no_type_hints(self):
        result = py_to_lean("def f(x):\n    return x\n")
        assert "def f " in result

    def test_empty_body(self):
        result = py_to_lean("def f() -> None:\n    pass\n")
        assert "def f " in result

    def test_if_else(self):
        result = py_to_lean("""def max(a: int, b: int) -> int:
    if a >= b:
        return a
    return b
""")
        assert "if a" in result
        assert "≥" in result or ">=" in result

    def test_recursion(self):
        result = py_to_lean("""def fact(n: int) -> int:
    if n <= 1:
        return 1
    return n * fact(n - 1)
""")
        assert "fact (n - 1)" in result or "fact(n - 1)" in result

    def test_multiple_params(self):
        result = py_to_lean(
            "def add(a: int, b: int, c: int) -> int:\n    return a + b + c\n"
        )
        assert "a + b + c" in result

    def test_string_concat(self):
        result = py_to_lean(
            "def greet(name: str) -> str:\n    return 'Hello, ' + name\n"
        )
        assert "name" in result


class TestPyToLeanOperators:
    def test_arithmetic(self):
        result = py_to_lean(
            "def f(x: int, y: int) -> int:\n    return (x + y) * (x - y)\n"
        )
        assert "+" in result
        assert "*" in result
        assert "-" in result

    def test_comparison(self):
        result = py_to_lean("""def cmp(x: int, y: int) -> bool:
    return x <= y and x >= y
""")
        assert "≤" in result or "<=" in result
        assert "∧" in result or "and" in result

    def test_equality(self):
        result = py_to_lean("""def eq(x: int, y: int) -> bool:
    return x == y
""")
        assert "==" in result or "=" in result


class TestPyToLeanEdgeCases:
    def test_chained_comparison(self):
        result = py_to_lean("""def between(x: int, a: int, b: int) -> bool:
    return a <= x <= b
""")
        assert result  # Should not crash

    def test_nested_calls(self):
        result = py_to_lean("""def f(x: int) -> int:
    return (x + 1) * (x + 2)
""")
        assert result

    def test_single_return(self):
        result = py_to_lean("def f() -> int:\n    return 42\n")
        assert "42" in result

    def test_no_return_annotation(self):
        result = py_to_lean("def f(x):\n    return x\n")
        assert result


class TestPyToLeanErrors:
    def test_invalid_syntax(self):
        with pytest.raises(SyntaxError):
            py_to_lean("def f(::\n")
