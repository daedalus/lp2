#!/usr/bin/env python3
"""Transpile mathlib .lean files to Python, preserving directory structure.

Usage:
    python run_step.py [--dry-run] [files...]

Without arguments, transpiles all files currently supported by the feature level.
"""

import argparse
import os
import sys
from pathlib import Path

MATHLIB_ROOT = Path(os.environ.get(
    "MATHLIB_ROOT",
    "/home/dclavijo/my_code/alphaproof-nexus/.lake/packages/mathlib/Mathlib",
))
OUTPUT_ROOT = Path(__file__).parent / "mathlib_python"

# Files known to work with Step 0 (basic Nat defs/theorems)
STEP0_FILES = [
    "Data/Nat/Dist.lean",
    "Data/Nat/Hyperoperation.lean",
    "Data/Nat/PSub.lean",
]


def transpile_file(lean_path: Path, relative: str, dry_run: bool = False) -> bool:
    """Transpile a single .lean file to .py under OUTPUT_ROOT.

    Returns True on success, False on failure.
    """
    out_path = OUTPUT_ROOT / relative.replace(".lean", ".py")
    if dry_run:
        print(f"  [dry-run] {lean_path}  ->  {out_path}")
        return True

    from lp2 import lean_to_py

    print(f"  {lean_path.name}  ->  {out_path}")
    try:
        with open(lean_path) as f:
            lean_code = f.read()
        py_code = lean_to_py(lean_code)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            f.write(py_code)
        return True
    except Exception as e:
        print(f"    FAIL: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Transpile mathlib -> Python")
    parser.add_argument("files", nargs="*", help="Specific files to transpile")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be done")
    parser.add_argument("--step", type=int, default=0, help="Feature maturity level")
    args = parser.parse_args()

    files = args.files or STEP0_FILES

    success = 0
    failure = 0
    for rel in files:
        lean_path = MATHLIB_ROOT / rel
        if not lean_path.exists():
            print(f"  MISSING: {lean_path}", file=sys.stderr)
            failure += 1
            continue
        if transpile_file(lean_path, rel, dry_run=args.dry_run):
            success += 1
        else:
            failure += 1

    print(f"\nDone: {success} succeeded, {failure} failed")
    return 0 if failure == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
