#!/usr/bin/env python3
import sys
import os

from lp2.parser.python_parser import parse_python
from lp2.parser.lean_parser import LeanParser
from lp2.codegen.python_codegen import generate_python
from lp2.codegen.lean4_codegen import generate_lean
from lp2.transpiler.python_to_lean4 import py_to_lean
from lp2.transpiler.lean4_to_python import lean_to_py


def convert_py_to_lean(source: str) -> str:
    py_ast = parse_python(source)
    lean_ast = py_to_lean(py_ast)
    return generate_lean(lean_ast)


def convert_lean_to_py(source: str) -> str:
    parser = LeanParser(source)
    lean_ast = parser.parse_module()
    py_ast = lean_to_py(lean_ast)
    return generate_python(py_ast)


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help'):
        print("Usage:")
        print("  lp2 py2lean <file.py>     Python -> Lean4")
        print("  lp2 lean2py <file.lean>   Lean4 -> Python")
        print("  lp2 py2lean --stdin       Read Python from stdin")
        print("  lp2 lean2py --stdin       Read Lean4 from stdin")
        sys.exit(0 if sys.argv[1:] else 1)

    direction = sys.argv[1]
    if direction == 'py2lean':
        if len(sys.argv) > 2 and sys.argv[2] == '--stdin':
            source = sys.stdin.read()
        elif len(sys.argv) > 2:
            with open(sys.argv[2]) as f:
                source = f.read()
        else:
            print("Usage: lp2 py2lean <file.py>")
            sys.exit(1)
        try:
            result = convert_py_to_lean(source)
            print(result)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    elif direction == 'lean2py':
        if len(sys.argv) > 2 and sys.argv[2] == '--stdin':
            source = sys.stdin.read()
        elif len(sys.argv) > 2:
            with open(sys.argv[2]) as f:
                source = f.read()
        else:
            print("Usage: lp2 lean2py <file.lean>")
            sys.exit(1)
        try:
            result = convert_lean_to_py(source)
            print(result)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Unknown command: {direction}")
        sys.exit(1)


if __name__ == '__main__':
    main()
