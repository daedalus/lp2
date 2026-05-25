__version__ = "0.1.1"
__all__ = [
    "py_to_lean",
    "lean_to_py",
    "convert_str",
    "convert_file",
]

from lp2.cli import convert_file, convert_str


def py_to_lean(source: str) -> str:
    """Translate Python source code to Lean 4.

    Args:
        source: Valid Python source with type hints.

    Returns:
        Equivalent Lean 4 source code.

    Raises:
        SyntaxError: If the Python source is invalid.
    """
    from lp2.codegen.lean4_codegen import generate_lean
    from lp2.parser.python_parser import parse_python
    from lp2.transpiler.python_to_lean4 import py_to_lean as _transform

    py_ast = parse_python(source)
    lean_ast = _transform(py_ast)
    return generate_lean(lean_ast)


def lean_to_py(source: str) -> str:
    """Translate Lean 4 source code to Python.

    Args:
        source: Valid Lean 4 source (supported subset).

    Returns:
        Equivalent Python source with type hints.

    Raises:
        SyntaxError: If the Lean source is invalid.
    """
    from lp2.codegen.python_codegen import generate_python
    from lp2.parser.lean_parser import LeanParser
    from lp2.transpiler.lean4_to_python import lean_to_py as _transform

    parser = LeanParser(source)
    lean_ast = parser.parse_module()
    py_ast = _transform(lean_ast)
    return generate_python(py_ast)
