"""Tests for CLI interface."""

import pytest

from lp2.cli import convert_file, convert_str, main


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

    def test_py2lean_with_file(self, tmp_path):
        import sys

        p = tmp_path / "test.py"
        p.write_text("def f(x: int) -> int:\n    return x + 1\n")
        old_argv = sys.argv
        sys.argv = ["lp2", "py2lean", str(p)]
        try:
            assert main() == 0
        finally:
            sys.argv = old_argv

    def test_py2lean_stdin(self):
        import sys
        from unittest.mock import patch

        old_argv = sys.argv
        sys.argv = ["lp2", "py2lean", "--stdin"]
        try:
            with patch(
                "sys.stdin.read", return_value="def f() -> int:\n    return 1\n"
            ):
                assert main() == 0
        finally:
            sys.argv = old_argv

    def test_py2lean_no_arg(self):
        import sys

        old_argv = sys.argv
        sys.argv = ["lp2", "py2lean"]
        try:
            assert main() == 1
        finally:
            sys.argv = old_argv

    def test_py2lean_parse_error(self, tmp_path):
        import sys

        p = tmp_path / "bad.py"
        p.write_text("def f(:\n")
        old_argv = sys.argv
        sys.argv = ["lp2", "py2lean", str(p)]
        try:
            assert main() == 1
        finally:
            sys.argv = old_argv

    def test_lean2py_with_file(self, tmp_path):
        import sys

        p = tmp_path / "test.lean"
        p.write_text("def f (x : Int) : Int := x + 1\n")
        old_argv = sys.argv
        sys.argv = ["lp2", "lean2py", str(p)]
        try:
            assert main() == 0
        finally:
            sys.argv = old_argv

    def test_lean2py_stdin(self):
        import sys
        from unittest.mock import patch

        old_argv = sys.argv
        sys.argv = ["lp2", "lean2py", "--stdin"]
        try:
            with patch("sys.stdin.read", return_value="def f : Int := 1\n"):
                assert main() == 0
        finally:
            sys.argv = old_argv

    def test_lean2py_no_arg(self):
        import sys

        old_argv = sys.argv
        sys.argv = ["lp2", "lean2py"]
        try:
            assert main() == 1
        finally:
            sys.argv = old_argv

    def test_lean2py_parse_error(self, tmp_path):
        import sys

        p = tmp_path / "bad.lean"
        p.write_text("def f : ,\n")
        old_argv = sys.argv
        sys.argv = ["lp2", "lean2py", str(p)]
        try:
            assert main() == 1
        finally:
            sys.argv = old_argv

    def test_unknown_command(self):
        import sys

        old_argv = sys.argv
        sys.argv = ["lp2", "bogus"]
        try:
            assert main() == 1
        finally:
            sys.argv = old_argv
