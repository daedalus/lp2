#!/usr/bin/env python3
"""
Demo: Round-trip transpilation of Fermat factorization (Python → Lean → Python)
using the lp2 bidirectional transpiler.

Demonstrates while-loop transpilation (while → let rec → def) end-to-end.
"""

import subprocess
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import lp2


def main():
    print("=== LP2: Python ↔ Lean Fermat Factorization Demo ===\n")

    with open(os.path.join(os.path.dirname(__file__), "fermat.py")) as f:
        python_source = f.read()

    print("1. Original Python source")
    print("-" * 50)
    print(python_source.strip())
    print()

    # ── Python → Lean ──
    print("2. Python → Lean")
    print("-" * 50)
    lean_source = lp2.py_to_lean(python_source)
    print(lean_source.strip())
    print()

    print("3. Verifying Lean output compiles")
    print("-" * 50)
    result = subprocess.run(
        ["lean", "--stdin"],
        input=lean_source,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print("  ✓ Compiles successfully (no errors)")
    else:
        print(f"  ✗ Compilation failed:\n{result.stderr}")
        sys.exit(1)
    print()

    # ── Lean → Python ──
    print("4. Lean → Python (round-trip)")
    print("-" * 50)
    python_roundtrip = lp2.lean_to_py(lean_source)
    print(python_roundtrip.strip())
    print()

    print("5. Verifying round-tripped Python is syntactically valid")
    print("-" * 50)
    try:
        import ast
        ast.parse(python_roundtrip)
        print("  ✓ Python AST parses without error")
    except SyntaxError as e:
        print(f"  ✗ Syntax error: {e}")
        sys.exit(1)
    print()

    print("=" * 60)
    print("Demo completed successfully!")


if __name__ == "__main__":
    main()
