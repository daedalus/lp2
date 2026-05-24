# SPEC.md — lp2

## Purpose

lp2 is a bidirectional source-to-source transpiler between Lean 4 and Python 3.
It converts Python functions with type hints into equivalent Lean 4 definitions,
and Lean 4 definitions into Python functions. The goal is to allow developers to
write code in either language and translate it to the other while preserving
semantics for a well-defined subset of each language.

## Scope

### What IS in scope

- **Functions**: Python `def` with type hints ⟷ Lean 4 `def`
- **Basic types**: `int`/`Int`/`Nat`, `float`/`Float`, `bool`/`Bool`, `str`/`String`, `None`/`Unit`
- **Container types**: `list`/`List`, `tuple`/`Prod`, `dict`/`HashMap`, `Optional`/`Option`
- **Arithmetic**: `+`, `-`, `*`, `/`, `%`, `**`/`^`
- **Comparisons**: `==`, `!=`, `<`, `<=`, `>`, `>=` with proper unicode mapping (`≤`, `≥`, `≠`)
- **Boolean logic**: `and`/`∧`, `or`/`∨`, `not`/`¬`
- **Conditionals**: `if`/`elif`/`else` ⟷ `if`/`then`/`else`
- **Pattern matching**: Python 3.10+ `match`/`case` ⟷ Lean 4 `match`/`with`
- **Recursion**: Self-recursive functions
- **Function application**: Curried Lean application ↔ multi-argument Python calls
- **Projections**: `expr.field` syntax in both languages
- **CLI**: `lp2 py2lean` and `lp2 lean2py` commands with file and stdin modes
- **Round-trip fidelity**: Translating Python→Lean→Python or Lean→Python→Lean produces equivalent code for supported constructs

### What is NOT in scope

- **Classes/OOP**: Python classes with methods beyond simple data structures
- **Monads/do-notation**: Lean `do` blocks with monadic effects
- **Tactics**: Lean `by` blocks, `calc`, `simp`
- **Dependent types**: Lean `∀`, `Π`, universe polymorphism, type-level computation
- **Propositions and proofs**: `theorem`, `lemma`, `axiom` beyond function signatures
- **Side effects**: Python `print()`, file I/O mapped to `IO` in Lean
- **Mutability**: Python mutable objects, Lean `mut`/`ST` Ref
- **Generators/async**: Python `yield`, `async`/`await`
- **Exception handling**: Python `try`/`except`/`raise`
- **Comprehensions**: List/dict/set comprehensions
- **Standard library**: Large standard library functions beyond basic built-ins
- **Foreign function interface**: FFI, C bindings

## Public API / Interface

### Python API

```python
from lp2 import py_to_lean, lean_to_py, convert_file, convert_str

def py_to_lean(source: str) -> str:
    """Translate Python source code to Lean 4 source code.

    Args:
        source: A string containing valid Python source code with type hints.

    Returns:
        A string containing the equivalent Lean 4 source code.

    Raises:
        SyntaxError: If the Python source is invalid or contains unsupported constructs.
        ValueError: If translation fails for a specific AST node.

    Example:
        >>> py_to_lean("def add(x: int, y: int) -> int:\\n    return x + y\\n")
        'def add (x : Int) (y : Int) : Int := x + y'
    """

def lean_to_py(source: str) -> str:
    """Translate Lean 4 source code to Python 3 source code.

    Args:
        source: A string containing valid Lean 4 source code (supported subset).

    Returns:
        A string containing the equivalent Python source code with type hints.

    Raises:
        SyntaxError: If the Lean source is invalid or contains unsupported constructs.
        ValueError: If translation fails for a specific AST node.

    Example:
        >>> lean_to_py("def add (x y : Int) : Int := x + y\\n")
        'def add(x: int, y: int) -> int:\\n    return x + y\\n'
    """

def convert_str(source: str, direction: str) -> str:
    """Translate source code in the given direction.

    Args:
        source: Source code string.
        direction: Either "py2lean" or "lean2py".

    Returns:
        Translated source code string.
    """

def convert_file(path: str, direction: str) -> str:
    """Read a file and translate it.

    Args:
        path: Path to the source file.
        direction: Either "py2lean" or "lean2py".

    Returns:
        Translated source code string.
    """
```

### CLI

```bash
lp2 py2lean <file.py>       # Translate Python file to Lean 4
lp2 lean2py <file.lean>     # Translate Lean 4 file to Python
lp2 py2lean --stdin          # Read Python from stdin
lp2 lean2py --stdin          # Read Lean 4 from stdin
lp2 --help                   # Show usage
```

Exit codes: 0 on success, 1 on error (invalid input, syntax error, etc.).

## Internal Architecture

```
src/lp2/
├── ast/           # AST node definitions for both languages
│   ├── python_ast.py     # Python-specific AST nodes
│   └── lean4_ast.py      # Lean 4-specific AST nodes
├── parser/        # Source → AST parsers
│   ├── python_parser.py  # Python source → Python AST (wraps stdlib ast)
│   ├── lean_lexer.py     # Lean 4 lexer/tokenizer
│   └── lean_parser.py    # Lean 4 token stream → Lean AST
├── codegen/       # AST → source code generators
│   ├── python_codegen.py # Python AST → Python source
│   └── lean4_codegen.py  # Lean AST → Lean 4 source
└── transpiler/    # AST-to-AST converters (the transpilation logic)
    ├── python_to_lean4.py  # Python AST → Lean AST
    └── lean4_to_python.py  # Lean AST → Python AST
```

Dependency direction: `parser/` and `codegen/` import from `ast/` only.
`transpiler/` imports from `ast/` only. `cli.py` and `__main__.py` import from
all subsystems but subsystems never import from the top level.

## Data Formats

### Input
- Python 3.10+ source code with type hints (PEP 484)
- Lean 4 source code using the `def` syntax (supported subset)
- Both via file path or stdin string

### Output
- Lean 4 source code with `def`, `:`, `:=` syntax
- Python 3.10+ source code with type hints
- UTF-8 encoding

## Edge Cases

1. **Empty function body**: A Python function with `pass` or no return should produce a Lean function returning `()`
2. **No type annotations**: Python functions without type hints produce Lean without type annotations; Lean defs without type annotations produce Python without type hints
3. **Recursive calls**: Self-recursive functions must round-trip correctly (no loop unrolling or inlining)
4. **Chained comparisons**: `a < b < c` in Python → `a < b && b < c` in Lean (must expand)
5. **Single-expression vs multi-statement bodies**: Python functions with a single `return` expr map to `:=`; multi-statement bodies with `if` + `return` must map to `if/then/else` expressions
6. **Empty match/pattern**: Match expressions with no arms produce valid fallback
7. **Nested function applications**: `f(g(x))` must preserve evaluation order and parentheses
8. **Operator precedence**: `a + b * c` must parse correctly in both directions
9. **Unicode operators**: Lean `≤`, `≥`, `≠`, `∧`, `∨` must round-trip to/from Python `<=`, `>=`, `!=`, `and`, `or`
10. **Function with multiple params**: Curried `f a b c` ↔ `f(a, b, c)` must work

## Performance & Constraints

- No external dependencies (stdlib only: `ast`, `dataclasses`)
- Input files up to 1MB must complete in < 5 seconds
- Must handle syntax errors gracefully with meaningful error messages
- Pure Python 3.11+ — no C extensions, no network calls
