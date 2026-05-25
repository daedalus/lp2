# LP² (lp2) — Lean ↔ Python, squared

**LP²** = LP² = LP × LP = **L**ean **↔ P**ython, squared for bidirectional. Translates in both directions: Python→Lean and Lean→Python.

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/master/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Translate Python functions with type hints into Lean 4 definitions, and Lean 4 definitions into Python functions.

## Install

```bash
pip install lp2
```

## Usage

### CLI

```bash
# Python → Lean4
lp2 py2lean my_file.py
lp2 py2lean --stdin < my_file.py

# Lean4 → Python
lp2 lean2py my_file.lean
lp2 lean2py --stdin < my_file.lean
```

### Python API

```python
from lp2 import py_to_lean, lean_to_py, convert_str, convert_file

lean_code = py_to_lean("def add(x: int, y: int) -> int:\n    return x + y\n")
py_code = lean_to_py("def add (x y : Int) : Int := x + y\n")

# Convenience
result = convert_str(source, "py2lean")
result = convert_file("input.py", "py2lean")
```

### Examples

For more comprehensive examples, see the `examples/` directory:
- `demo_theorem_transpilation.py`: Shows how to transpile mathematical theorems from Lean to Python as computable Boolean-valued functions
- `fermat.py`: Example related to Fermat's Last Theorem
- `simple_while.py`: Simple while loop example

**Python → Lean4:**

```python
def fib(n: int) -> int:
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)
```

```lean4
def fib (n : Int) : Int :=
  if n ≤ 1 then n else fib (n - 1) + fib (n - 2)
```

**Lean4 → Python:**

```lean4
def isZero (n : Int) : Bool := match n with
  | 0 => true
  | _ => false
```

```python
def isZero(n: int) -> bool:
    match n:
        case 0:
            return True
        case _:
            return False
```

## Development

```bash
pip install -e ".[test]"
pytest
ruff format src/ tests/
prospector --with-tool ruff --with-tool mypy src/
```

## License

MIT
