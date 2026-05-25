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
- `factorial_algorithms.py` / `factorial_algorithms_test.py` / `factorial_algorithms.lean`: Multiple factorial algorithms (iterative, product tree, prime swing) with `@no_transpile` for unsupported features
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

### `no_transpile` — skipping unsupported Python features

When the transpiler encounters a Python feature it cannot translate (e.g.,
generators, comprehensions, bytearray, f-strings), it raises an error by default.
You can mark any function or statement with `@no_transpile` to keep the original
Python source in the output as a Lean comment:

```python
@no_transpile
def sieve(n: int) -> list[int]:
    bs = bytearray(b"\x01") * (n + 1)
    bs[0:2] = b"\x00\x00"
    return [i for i in range(2, n + 1) if bs[i]]
```

Generates:

```lean4
-- no_transpile (@sieve)
--   def sieve(n: int) -> list[int]:
--       bs = bytearray(b"\x01") * (n + 1)
--       ...
```

For individual lines, use a `# no_transpile` comment:

```python
sys.set_int_max_str_digits(100000)  # no_transpile
```

Both annotations are **parser-only** and never executed at Python runtime.

### Stdlib source-following for imported functions

When the transpiler sees `import math`, it imports the module at transpile time.
If it encounters `math.factorial(x)`, it attempts to retrieve the function's
source via `inspect.getsource` and transpile it automatically. For C-extension
functions (like `math.factorial`), where no Python source exists, it falls back
to transpiling a known Python implementation:

```lean4
partial def factorial (n : Nat) : Nat :=
  let result := 1; let rec loop (i : Nat) (result : Nat) : Nat :=
    if i < n + 1 then loop (i + 1) (result * i) else result; loop 2 result
```

This avoids maintaining a brittle mapping from Python stdlib names to Lean
library paths. Pure-Python functions from `functools`, `collections`, etc. can
be auto-transpiled in the same way. Only functions where source retrieval fails
_and_ no fallback exists require `@no_transpile`.

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

Python's `+` on lists means **concatenation**. Lean 4.30.0-rc2 defines `Add (List α)`
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

### No `Std` or `mathlib4` available

The transpiler targets Lean 4.30.0-rc2 without `Std` or `mathlib4`.
Features like `omega`, `List.range`, `HashMap`, `Nat.factorial`, and `Nat.popCount`
are unavailable from the standard library. The transpiler compensates with:

- A built-in `partial def get` helper for list indexing (bypassing `Fin` proof
  requirements)
- A built-in `Nat.popCount` shim (bit-count via recursion)
- Stdlib source-following (see above) to synthesize implementations from
  equivalent Python code
- `@no_transpile` as the escape hatch for anything that cannot be synthesized

### Unsupported Python features

These Python constructs have no Lean equivalent or are not yet implemented:

- Generators / `yield`
- `async` / `await`
- Decorators (except the special `@no_transpile`)
- Exception handling (`try`/`except`/`finally`)
- `with` statements (context managers)
- List/dict/set comprehensions
- `*args` / `**kwargs` (variadic functions)
- Classes with methods (only simple data structures supported)
- Augmented assignment on lists (`xs += [x]`)
- F-strings, slice assignment, `dict`/`set` mutation

## Development

```bash
pip install -e ".[test]"
pytest
ruff format src/ tests/
prospector --with-tool ruff --with-tool mypy src/
```

## License

MIT
