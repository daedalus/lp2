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
- `demo_factorial_roundtrip.py` / `factorial.py`: Recursive factorial (Python → Lean → Python)
- `demo_fibonacci_roundtrip.py` / `fibonacci.py`: Recursive Fibonacci
- `demo_bubble_sort_roundtrip.py` / `bubble_sort.py`: Bubble sort with nested while loops
- `demo_quicksort_roundtrip.py` / `quicksort.py`: Quicksort with for-loop + `if/elif/else`
- `demo_fermat_roundtrip.py` / `fermat.py`: Fermat factorization with while loops
- `demo_theorem_transpilation.py`: Transpile Lean theorems to Python as Boolean-valued functions
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

## Caveats & Limitations

### Termination on `Int` recursion

Lean's termination checker cannot prove well-foundedness for recursion over `Int`.
The transpiler auto-detects self-recursive calls and emits `partial def` for such
functions. This sidesteps termination checking but means Lean cannot verify the
function always halts.

```python
def factorial(n: int) -> int:
    if n <= 1:
        return 1
    return n * factorial(n - 1)
```

```lean4
partial def factorial (n : Int) : Int :=
  if n ≤ 1 then 1 else n * factorial (n - 1)
```

### `+` on lists (Python concatenation vs. Lean element-wise addition)

Python's `+` on lists means **concatenation**. Lean 4.29.1 defines `Add (List α)`
as element-wise addition (`zipWith`). The transpiler emits a `local instance`
that overrides `Add (List Int)` to use `List.append`, so `+` on `List Int`
concatenates as expected. This only covers `List Int` — other list types (e.g.,
`List Float`, `List String`) remain element-wise.

### List mutation is silently dropped

In-place list mutation (`xs[i] = x`, `xs.append(x)`) is not supported. The
transpiler silently drops these statements. Use immutable patterns instead:

```python
# Instead of:
#   xs[i] = x
#   xs.append(x)

# Use:
#   xs = xs[:i] + [x] + xs[i+1:]
#   xs = xs + [x]
```

### Round-trip is lossy

Transpiling Python → Lean → Python recovers syntactically valid Python code but
loses some information:

| Lost detail | Example | Round-trip result |
|---|---|---|
| `//` (int division) | `x // y` | `x / y` |
| `tuple` type | `(1, 2)` → `Prod.mk` | parsed as generic call |
| Return type annotations | `def f() -> int:` | `def f():` |
| `for` / `while` loops | `let rec` / `match` | parser skips (not yet supported) |
| Nested `let` chains | `let a := ...; let b := ...` | may produce unusual `def` wrappers |

### No `Std` library available

The evaluator (`lean --stdin`) runs Lean 4.29.1 without the `Std` library.
Features like `omega`, `List.range`, and `HashMap` are unavailable. The
transpiler uses a built-in `partial def get` helper for list indexing
(bypassing `Fin` proof requirements).

### Unsupported Python features

These Python constructs have no Lean equivalent or are not yet implemented:

- Generators / `yield`
- `async` / `await`
- Decorators
- Exception handling (`try`/`except`/`finally`)
- `with` statements (context managers)
- List/dict/set comprehensions
- `*args` / `**kwargs` (variadic functions)
- Classes with methods (only simple data structures supported)
- Augmented assignment on lists (`xs += [x]`)

## Development

```bash
pip install -e ".[test]"
pytest
ruff format src/ tests/
prospector --with-tool ruff --with-tool mypy src/
```

## License

MIT
