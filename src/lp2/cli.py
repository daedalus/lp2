#!/usr/bin/env python3
import sys

from lp2.parser.python_parser import parse_python
from lp2.parser.lean_parser import LeanParser
from lp2.codegen.python_codegen import generate_python
from lp2.codegen.lean4_codegen import generate_lean
from lp2.transpiler.python_to_lean4 import py_to_lean
from lp2.transpiler.lean4_to_python import lean_to_py


def convert_str(source: str, direction: str) -> str:
    if direction == "py2lean":
        return convert_py_to_lean(source)
    elif direction == "lean2py":
        return convert_lean_to_py(source)
    raise ValueError(f"Unknown direction: {direction}")


def convert_file(path: str, direction: str) -> str:
    with open(path) as f:
        source = f.read()
    return convert_str(source, direction)


def convert_py_to_lean(source: str) -> str:
    py_ast = parse_python(source)
    lean_ast = py_to_lean(py_ast)
    return generate_lean(lean_ast)


def convert_lean_to_py(source: str) -> str:
    parser = LeanParser(source)
    lean_ast = parser.parse_module()
    py_ast = lean_to_py(lean_ast)
    return generate_python(py_ast)


def _print_usage() -> int:
    print("Usage:")
    print("  lp2 py2lean <file.py>     Python -> Lean4")
    print("  lp2 lean2py <file.lean>   Lean4 -> Python")
    print("  lp2 py2lean --stdin       Read Python from stdin")
    print("  lp2 lean2py --stdin       Read Lean4 from stdin")
    return 0 if len(sys.argv) > 1 else 1


def _handle_py2lean() -> int:
    if len(sys.argv) > 2 and sys.argv[2] == "--stdin":
        source = sys.stdin.read()
    elif len(sys.argv) > 2:
        with open(sys.argv[2]) as f:
            source = f.read()
    else:
        print("Usage: lp2 py2lean <file.py>")
        return 1
    try:
        result = convert_py_to_lean(source)
        print(result)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _handle_lean2py() -> int:
    if len(sys.argv) > 2 and sys.argv[2] == "--stdin":
        source = sys.stdin.read()
    elif len(sys.argv) > 2:
        with open(sys.argv[2]) as f:
            source = f.read()
    else:
        print("Usage: lp2 lean2py <file.lean>")
        return 1
    try:
        result = convert_lean_to_py(source)
        print(result)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        return _print_usage()

    direction = sys.argv[1]
    if direction == "py2lean":
        return _handle_py2lean()
    elif direction == "lean2py":
        return _handle_lean2py()
    else:
        print(f"Unknown command: {direction}")
        return 1
