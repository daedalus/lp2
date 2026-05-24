# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-05-24

### Added
- Initial release
- Python → Lean4 transpiler (functions, types, if/else, recursion, match)
- Lean4 → Python transpiler (def, match, if/then/else, type annotations)
- Custom Lean4 lexer and recursive-descent parser
- CLI interface (lp2 py2lean / lp2 lean2py)
- Python API (py_to_lean, lean_to_py, convert_str, convert_file)
- Full pytest suite with 42 tests
- Round-trip fidelity for supported constructs

[0.1.0]: https://github.com/daedalus/lp2/releases/tag/v0.1.0
