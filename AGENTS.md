# LP2 — Lean4 ↔ Python Bidirectional Transpiler

## Module scope

Bidirectional transpiler between Python 3.11+ and Lean 4. ~25 core files in `src/lp2/`. Each direction is a 4-stage pipeline: **parse → transpile → codegen**.

## Architecture (2 sentences)

- **Python → Lean**: `parse_python()` → `py_to_lean()` → `generate_lean()`
- **Lean → Python**: `LeanParser().parse()` → `lean_to_py()` → `generate_python()`
- Public API: `lp2.py_to_lean(str) -> str` and `lp2.lean_to_py(str) -> str` (both in `src/lp2/__init__.py`)

## Examples

See the `examples/` directory for demonstrations:
- `demo_theorem_transpilation.py`: Shows how to transpile mathematical theorems from Lean to Python as computable Boolean-valued functions
- `fermat.py`: Example related to Fermat's Last Theorem
- `simple_while.py`: Simple while loop example

## Procedural workflow

### Add a new AST node

1. Add the dataclass to `src/lp2/ast/python_ast.py` or `lean4_ast.py` (inherit `PyNode`/`LeanNode`).
2. Add parsing in `python_parser.py` or `lean_parser.py` (find the `isinstance` chain for the closest node).
3. Add conversion in `transpiler/python_to_lean4.py` or `lean4_to_python.py`.
4. Add codegen in `codegen/python_codegen.py` or `lean4_codegen.py`.
5. Add roundtrip tests in `tests/`.

### Run quality gates

```bash
ruff check src/ tests/ && ruff format src/ tests/ && mypy src/ && pytest
```

### Actual bugs vs type noise

Mypy may flag `list` invariance across AST node types — these are not runtime bugs (Python lists are covariant at runtime). Only worry about mypy errors NOT in the override list in `pyproject.toml:[[tool.mypy.overrides]]`.

## Don't / Do

- ❌ Don't add `setup.py` or `setup.cfg`. ✅ Use `pyproject.toml` with hatchling.
- ❌ Don't add `# type: ignore` for structural `list` invariance. ✅ Add error codes to the mypy override in `pyproject.toml`.
- ❌ Don't call `_peek(offset)` on `LeanParser` — it now supports offset. ✅ Uses `self._peek(n)` for lookahead in `lean_parser.py`.
- ❌ Don't import individual AST classes. ✅ Use `from lp2.ast.lean4_ast import *` / `from lp2.ast.python_ast import *` (star imports are intentional).

## Decision table: which direction to implement

| Task | Parse | Transpile | Codegen |
|------|-------|-----------|---------|
| Convert Python source to Lean source | `python_parser.py` | `python_to_lean4.py` | `lean4_codegen.py` |
| Convert Lean source to Python source | `lean_parser.py` | `lean4_to_python.py` | `python_codegen.py` |
