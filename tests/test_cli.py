"""Tests for CLI interface."""

import pytest
from lp2.cli import convert_str, convert_file, main


class TestConvertStr:
    def test_py_to_lean(self):
        result = convert_str("def f(x: int) -> int:\n    return x + 1\n", "py2lean")
        assert "def f" in result

    def test_lean_to_py(self):
        result = convert_str("def f (x : Int) : Int := x + 1\n", "lean2py")
        assert "def f" in result

    def test_invalid_direction(self):
        with pytest.raises(ValueError, match="Unknown direction"):
            convert_str("x", "unknown")


class TestConvertFile:
    def test_py_file(self, tmp_path):
        p = tmp_path / "test.py"
        p.write_text("def f(x: int) -> int:\n    return x + 1\n")
        result = convert_file(str(p), "py2lean")
        assert "def f" in result

    def test_lean_file(self, tmp_path):
        p = tmp_path / "test.lean"
        p.write_text("def f (x : Int) : Int := x + 1\n")
        result = convert_file(str(p), "lean2py")
        assert "def f" in result


class TestCliMain:
    def test_help_exit(self):
        import sys

        old_argv = sys.argv
        sys.argv = ["lp2", "--help"]
        try:
            assert main() == 0
        finally:
            sys.argv = old_argv

    def test_no_args_exit(self):
        import sys

        old_argv = sys.argv
        sys.argv = ["lp2"]
        try:
            assert main() == 1
        finally:
            sys.argv = old_argv
