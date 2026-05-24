from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


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
    value: Optional[PyExpr]


@dataclass
class PyAssign(PyStmt):
    target: PyNode
    value: PyExpr
    type_annotation: Optional[PyExpr] = None


@dataclass
class PyAnnAssign(PyStmt):
    target: PyExpr
    annotation: PyExpr
    value: Optional[PyExpr]


@dataclass
class PyFunctionDef(PyStmt):
    name: str
    args: list[tuple[str, Optional[PyExpr], Optional[PyExpr]]]
    return_type: Optional[PyExpr]
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
    guard: Optional[PyExpr]
    body: list[PyStmt]


@dataclass
class PyImport(PyStmt):
    names: list[str]


@dataclass
class PyRaise(PyStmt):
    exc: PyExpr


@dataclass
class PyTry(PyStmt):
    body: list[PyStmt]
    handlers: list[PyExceptHandler]
    orelse: list[PyStmt] = field(default_factory=list)
    finalbody: list[PyStmt] = field(default_factory=list)


@dataclass
class PyExceptHandler(PyNode):
    typ: Optional[PyExpr]
    name: Optional[str]
    body: list[PyStmt]


@dataclass
class PyWith(PyStmt):
    items: list[PyNode]
    body: list[PyStmt]


@dataclass
class PyAssert(PyStmt):
    test: PyExpr
    msg: Optional[PyExpr]


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
class PyAsyncFunctionDef(PyStmt):
    name: str
    args: list[tuple[str, Optional[PyExpr], Optional[PyExpr]]]
    return_type: Optional[PyExpr]
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
    kind: Optional[str] = None


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
    lower: Optional[PyExpr]
    upper: Optional[PyExpr]
    step: Optional[PyExpr]


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
    keys: list[Optional[PyExpr]]
    values: list[PyExpr]


@dataclass
class PyLambda(PyExpr):
    args: list[tuple[str, Optional[PyExpr]]]
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
    value: Optional[PyExpr]


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
