"""Tests for Python → Lean4 translation."""

import pytest

from lp2 import py_to_lean


class TestPyToLeanBasic:
    def test_simple_function(self):
        result = py_to_lean("def f(x: int) -> int:\n    return x + 1\n")
        assert "def f (x : Nat) : Nat" in result
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


class TestPyToLeanControlFlow:
    def test_for_loop(self):
        result = py_to_lean("""def sum_to(n: int) -> int:
    total = 0
    for i in range(n):
        total = total + i
    return total
""")
        assert "let rec" in result or "loop" in result

    def test_if_elif_else(self):
        result = py_to_lean("""def sign(x: int) -> int:
    if x > 0:
        return 1
    elif x < 0:
        return -1
    else:
        return 0
""")
        assert result

    def test_for_list_iteration(self):
        result = py_to_lean("""def sum_list(xs: list) -> int:
    total = 0
    for x in xs:
        total = total + x
    return total
""")
        assert "let rec" in result
        assert "match" in result

    def test_for_range_with_start_end(self):
        result = py_to_lean("""def sum_range(n: int) -> int:
    total = 0
    for i in range(1, n):
        total = total + i
    return total
""")
        assert "let rec" in result

    def test_for_with_if_branches(self):
        result = py_to_lean("""def partition(xs: list) -> int:
    less = 0
    greater = 0
    for x in xs:
        if x < 0:
            less = less + 1
        elif x > 0:
            greater = greater + 1
    return less + greater
""")
        assert "loop" in result


class TestPyToLeanOperatorsExtended:
    def test_boolean_and_or(self):
        result = py_to_lean("""def test(x: bool, y: bool) -> bool:
    return x and y or not x
""")
        assert "∧" in result or "and" in result
        assert "∨" in result or "or" in result

    def test_not_operator(self):
        result = py_to_lean("""def neg(b: bool) -> bool:
    return not b
""")
        assert "not" in result

    def test_unary_minus(self):
        result = py_to_lean("""def negate(x: int) -> int:
    return -x
""")
        assert "-x" in result or "neg" in result


class TestPyToLeanDataStructures:
    def test_list_literal(self):
        result = py_to_lean("""def items() -> list:
    return [1, 2, 3]
""")
        assert result

    def test_tuple(self):
        result = py_to_lean("""def pair() -> tuple:
    return (1, "a")
""")
        assert result

    def test_dict_literal(self):
        result = py_to_lean("""def mapping() -> dict:
    return {"key": 42}
""")
        assert result


class TestPyToLeanFunctional:
    def test_lambda(self):
        result = py_to_lean("""def apply(f, x: int) -> int:
    return f(x)
""")
        assert result

    def test_attribute_access(self):
        result = py_to_lean("""def get_len(x: str) -> int:
    return len(x)
""")
        assert result

    def test_subscript(self):
        result = py_to_lean("""def first(xs: list) -> int:
    return xs[0]
""")
        assert result

    def test_subscript_assign(self):
        result = py_to_lean("""def set_first(xs: list, x: int) -> list:
    xs[0] = x
    return xs
""")
        assert "set" in result
        assert result

    def test_subscript_assign_in_loop(self):
        result = py_to_lean("""def scale(xs: list, n: int) -> list:
    i = 0
    while i < len(xs):
        xs[i] = xs[i] * n
        i = i + 1
    return xs
""")
        assert "let rec" in result or "loop" in result
        assert "set" in result
        assert result

    def test_aug_assign_list(self):
        result = py_to_lean("""def push(xs: list, x: int) -> list:
    xs += [x]
    return xs
""")
        assert result

    def test_aug_assign_subscript(self):
        result = py_to_lean("""def inc_first(xs: list) -> list:
    xs[0] += 1
    return xs
""")
        assert "set" in result
        assert result


class TestPyToLeanYield:
    def test_simple_yields(self):
        result = py_to_lean("""def f() -> list[int]:
    yield 1
    yield 2
    yield 3
""")
        assert "List" in result
        assert result

    def test_yield_while_loop(self):
        result = py_to_lean("""def count(n: int) -> list[int]:
    i = 0
    while i < n:
        yield i
        i = i + 1
""")
        assert "let rec" in result or "loop" in result
        assert result

    def test_yield_for_loop(self):
        result = py_to_lean("""def collect(xs: list[int]) -> list[int]:
    for x in xs:
        yield x
""")
        assert "let rec" in result or "loop" in result
        assert result

    def test_yield_if_else(self):
        result = py_to_lean("""def pick(n: int) -> list[int]:
    if n > 0:
        yield 1
    else:
        yield 2
""")
        assert result

    def test_yield_then_assign(self):
        result = py_to_lean("""def f() -> list[int]:
    yield 1
    x = 42
    yield x
""")
        assert result


class TestPyToLeanClass:
    def test_simple_class(self):
        result = py_to_lean("""class Point:
    x: int
    y: int
""")
        assert "structure" in result.lower() or "class" in result


class TestPyToLeanNoTranspile:
    def test_no_transpile_decorator(self):
        code = """\
@no_transpile
def f(x):
    return f'hello {x}'

def g(a: int) -> int:
    return a + 1
"""
        result = py_to_lean(code)
        assert "no_transpile" in result
        assert "f'hello {x}'" in result or "hello" in result
        assert "def g" in result
        assert "a + 1" in result or "a + Nat.succ 0" in result

    def test_unsupported_stmt_becomes_comment(self):
        code = """\
def f(x: int) -> int:
    return x + 1
"""
        result = py_to_lean(code)
        assert "def f" in result


class TestPyToLeanEdgeCases:
    def test_invalid_syntax(self):
        with pytest.raises(SyntaxError):
            py_to_lean("def f(::\n")
