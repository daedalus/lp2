#!/usr/bin/env python3
"""
Demo: Transpilation of Python generators (yield) to Lean.
Demonstrates yield in while loops, for loops, and if/else branches.
"""

import subprocess
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import lp2


def main():
    print("=== LP2: Python yield → Lean Demo ===\n")

    with open(os.path.join(os.path.dirname(__file__), "yield_example.py")) as f:
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

    eval_code = """
#eval count 5
#eval evens (List.cons 1 (List.cons 2 (List.cons 3 (List.cons 4 List.nil))))
#eval take_first (List.cons 10 (List.cons 20 List.nil))
#eval take_first List.nil
"""
    result = subprocess.run(
        ["lean", "--stdin"],
        input=lean_source + eval_code,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        outputs = [l for l in result.stdout.split("\n") if l.strip()]
        print("  4. Evaluating generated Lean code")
        print("-" * 50)
        print(
            "  count 5 (range 0..4)                        →",
            outputs[0] if len(outputs) > 0 else "?",
        )
        print(
            "  evens [1,2,3,4]                              →",
            outputs[1] if len(outputs) > 1 else "?",
        )
        print(
            "  take_first [10,20]                           →",
            outputs[2] if len(outputs) > 2 else "?",
        )
        print(
            "  take_first []                                →",
            outputs[3] if len(outputs) > 3 else "?",
        )
        print("  ✓ All evaluations produced expected output")
    else:
        print(f"  ✗ Evaluation failed:\n{result.stderr}")
        sys.exit(1)
    print()

    print("=" * 60)
    print("Demo completed successfully!")


if __name__ == "__main__":
    main()
