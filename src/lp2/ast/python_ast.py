from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PyNode:
    pass


@dataclass
class PyModule(PyNode):
    body: list[PyNode]


@dataclass
class PyExpr(PyNode):
    pass


@dataclass
class PyStmt(PyNode):
    pass


@dataclass
class PyReturn(PyStmt):
    value: PyExpr | None


@dataclass
class PyAssign(PyStmt):
    target: PyNode
    value: PyExpr
    type_annotation: PyExpr | None = None


@dataclass
class PyAugAssign(PyStmt):
    target: PyExpr
    op: str
    value: PyExpr


@dataclass
class PyAnnAssign(PyStmt):
    target: PyExpr
    annotation: PyExpr
    value: PyExpr | None


@dataclass
class PyFunctionDef(PyStmt):
    name: str
    args: list[tuple[str, PyExpr | None, PyExpr | None]]
    return_type: PyExpr | None
    body: list[PyStmt]
    decorators: list[PyExpr] = field(default_factory=list)


@dataclass
class PyClassDef(PyStmt):
    name: str
    bases: list[PyExpr]
    body: list[PyStmt]


@dataclass
class PyIf(PyStmt):
    test: PyExpr
    body: list[PyStmt]
    orelse: list[PyStmt]


@dataclass
class PyFor(PyStmt):
    target: PyExpr
    iter: PyExpr
    body: list[PyStmt]


@dataclass
class PyWhile(PyStmt):
    test: PyExpr
    body: list[PyStmt]


@dataclass
class PyExprStmt(PyStmt):
    expr: PyExpr


@dataclass
class PyPass(PyStmt):
    pass


@dataclass
class PyBreak(PyStmt):
    pass


@dataclass
class PyContinue(PyStmt):
    pass


@dataclass
class PyMatch(PyStmt):
    subject: PyExpr
    cases: list[PyMatchCase]


@dataclass
class PyMatchCase(PyNode):
    pattern: PyExpr
    guard: PyExpr | None
    body: list[PyStmt]


@dataclass
class PyImport(PyStmt):
    names: list[str]


@dataclass
class PyRaise(PyStmt):
    exc: PyExpr | None


@dataclass
class PyTry(PyStmt):
    body: list[PyStmt]
    handlers: list[PyExceptHandler]
    orelse: list[PyStmt] = field(default_factory=list)
    finalbody: list[PyStmt] = field(default_factory=list)


@dataclass
class PyExceptHandler(PyNode):
    typ: PyExpr | None
    name: str | None
    body: list[PyStmt]


@dataclass
class PyWith(PyStmt):
    items: list[PyNode]
    body: list[PyStmt]


@dataclass
class PyAssert(PyStmt):
    test: PyExpr
    msg: PyExpr | None


@dataclass
class PyGlobal(PyStmt):
    names: list[str]


@dataclass
class PyNonlocal(PyStmt):
    names: list[str]


@dataclass
class PyDelete(PyStmt):
    targets: list[PyExpr]


@dataclass
class PySkipTranspile(PyStmt):
    """Marker for code that should not be transpiled (e.g. @no_transpile).

    Stores the raw source lines so they can be emitted as Lean comments.
    """
    source_lines: list[str]
    reason: str = ""


@dataclass
class PyAsyncFunctionDef(PyStmt):
    name: str
    args: list[tuple[str, PyExpr | None, PyExpr | None]]
    return_type: PyExpr | None
    body: list[PyStmt]


@dataclass
class PyAsyncFor(PyStmt):
    target: PyExpr
    iter: PyExpr
    body: list[PyStmt]


@dataclass
class PyAsyncWith(PyStmt):
    items: list[PyNode]
    body: list[PyStmt]


@dataclass
class PyName(PyExpr):
    id: str


@dataclass
class PyConstant(PyExpr):
    value: object
    kind: str | None = None


@dataclass
class PyBinOp(PyExpr):
    left: PyExpr
    op: str
    right: PyExpr


@dataclass
class PyUnaryOp(PyExpr):
    op: str
    operand: PyExpr


@dataclass
class PyCompare(PyExpr):
    left: PyExpr
    ops: list[str]
    comparators: list[PyExpr]


@dataclass
class PyBoolOp(PyExpr):
    op: str
    values: list[PyExpr]


@dataclass
class PyCall(PyExpr):
    func: PyExpr
    args: list[PyExpr]
    kwargs: list[tuple[str, PyExpr]] = field(default_factory=list)


@dataclass
class PyIfExp(PyExpr):
    test: PyExpr
    body: PyExpr
    orelse: PyExpr


@dataclass
class PyAttribute(PyExpr):
    value: PyExpr
    attr: str


@dataclass
class PySubscript(PyExpr):
    value: PyExpr
    slice: PyExpr


@dataclass
class PySlice(PyExpr):
    lower: PyExpr | None
    upper: PyExpr | None
    step: PyExpr | None


@dataclass
class PyList(PyExpr):
    elts: list[PyExpr]


@dataclass
class PyTuple(PyExpr):
    elts: list[PyExpr]


@dataclass
class PySet(PyExpr):
    elts: list[PyExpr]


@dataclass
class PyDict(PyExpr):
    keys: list[PyExpr | None]
    values: list[PyExpr]


@dataclass
class PyLambda(PyExpr):
    args: list[tuple[str, PyExpr | None]]
    body: PyExpr


@dataclass
class PyListComp(PyExpr):
    elt: PyExpr
    generators: list[PyComprehension]


@dataclass
class PySetComp(PyExpr):
    elt: PyExpr
    generators: list[PyComprehension]


@dataclass
class PyDictComp(PyExpr):
    key: PyExpr
    value: PyExpr
    generators: list[PyComprehension]


@dataclass
class PyComprehension(PyNode):
    target: PyExpr
    iter: PyExpr
    ifs: list[PyExpr]
    is_async: bool = False


@dataclass
class PyStarred(PyExpr):
    value: PyExpr


@dataclass
class PyAwait(PyExpr):
    value: PyExpr


@dataclass
class PyYield(PyExpr):
    value: PyExpr | None


@dataclass
class PyYieldFrom(PyExpr):
    value: PyExpr


@dataclass
class PyFormattedStr(PyExpr):
    values: list[PyExpr]


@dataclass
class PyJoinedStr(PyExpr):
    values: list[PyExpr]


@dataclass
class PyWalrus(PyExpr):
    target: PyExpr
    value: PyExpr


@dataclass
class PyTypeAlias(PyStmt):
    name: PyExpr
    value: PyExpr


@dataclass
class PyMatchOr(PyExpr):
    """OR pattern inside a match case: ``case 0 | 1 | 2:``."""

    patterns: list[PyExpr]
