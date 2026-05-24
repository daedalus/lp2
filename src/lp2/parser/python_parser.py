import ast as py_ast
from lp2.ast.python_ast import *


_TYPE_MAP = {
    int: "int",
    float: "float",
    bool: "bool",
    str: "str",
    bytes: "bytes",
    type(None): "None",
}


_BINOP_MAP = {
    py_ast.Add: "+",
    py_ast.Sub: "-",
    py_ast.Mult: "*",
    py_ast.Div: "/",
    py_ast.FloorDiv: "//",
    py_ast.Mod: "%",
    py_ast.Pow: "**",
    py_ast.LShift: "<<",
    py_ast.RShift: ">>",
    py_ast.BitOr: "|",
    py_ast.BitXor: "^",
    py_ast.BitAnd: "&",
    py_ast.MatMult: "@",
}

_UNARYOP_MAP = {
    py_ast.UAdd: "+",
    py_ast.USub: "-",
    py_ast.Not: "not",
    py_ast.Invert: "~",
}

_CMPOP_MAP = {
    py_ast.Eq: "==",
    py_ast.NotEq: "!=",
    py_ast.Lt: "<",
    py_ast.LtE: "<=",
    py_ast.Gt: ">",
    py_ast.GtE: ">=",
    py_ast.Is: "is",
    py_ast.IsNot: "is not",
    py_ast.In: "in",
    py_ast.NotIn: "not in",
}

_BOOLOP_MAP = {
    py_ast.And: "and",
    py_ast.Or: "or",
}


def parse_python(source: str) -> PyModule:
    tree = py_ast.parse(source)
    return _convert_module(tree)


def _convert_module(node: py_ast.Module) -> PyModule:
    return PyModule(body=[_convert_stmt(s) for s in node.body])


def _convert_stmt(node: py_ast.stmt) -> PyStmt:
    if isinstance(node, py_ast.FunctionDef):
        return PyFunctionDef(
            name=node.name,
            args=_convert_args(node.args),
            return_type=_convert_expr(node.returns) if node.returns else None,
            body=[_convert_stmt(s) for s in node.body],
            decorators=[_convert_expr(d) for d in node.decorator_list],
        )
    elif isinstance(node, py_ast.AsyncFunctionDef):
        return PyAsyncFunctionDef(
            name=node.name,
            args=_convert_args(node.args),
            return_type=_convert_expr(node.returns) if node.returns else None,
            body=[_convert_stmt(s) for s in node.body],
        )
    elif isinstance(node, py_ast.ClassDef):
        return PyClassDef(
            name=node.name,
            bases=[_convert_expr(b) for b in node.bases],
            body=[_convert_stmt(s) for s in node.body],
        )
    elif isinstance(node, py_ast.Return):
        return PyReturn(value=_convert_expr(node.value) if node.value else None)
    elif isinstance(node, py_ast.Assign):
        targets = node.targets
        if len(targets) == 1:
            return PyAssign(
                target=_convert_expr(targets[0]),
                value=_convert_expr(node.value),
            )
        else:
            return PyAssign(
                target=PyTuple(elts=[_convert_expr(t) for t in targets]),
                value=_convert_expr(node.value),
            )
    elif isinstance(node, py_ast.AnnAssign):
        return PyAnnAssign(
            target=_convert_expr(node.target),
            annotation=_convert_expr(node.annotation),
            value=_convert_expr(node.value) if node.value else None,
        )
    elif isinstance(node, py_ast.If):
        return PyIf(
            test=_convert_expr(node.test),
            body=[_convert_stmt(s) for s in node.body],
            orelse=[_convert_stmt(s) for s in node.orelse],
        )
    elif isinstance(node, py_ast.For):
        return PyFor(
            target=_convert_expr(node.target),
            iter=_convert_expr(node.iter),
            body=[_convert_stmt(s) for s in node.body],
        )
    elif isinstance(node, py_ast.AsyncFor):
        return PyAsyncFor(
            target=_convert_expr(node.target),
            iter=_convert_expr(node.iter),
            body=[_convert_stmt(s) for s in node.body],
        )
    elif isinstance(node, py_ast.While):
        return PyWhile(
            test=_convert_expr(node.test),
            body=[_convert_stmt(s) for s in node.body],
        )
    elif isinstance(node, py_ast.Expr):
        return PyExprStmt(expr=_convert_expr(node.value))
    elif isinstance(node, py_ast.Pass):
        return PyPass()
    elif isinstance(node, py_ast.Break):
        return PyBreak()
    elif isinstance(node, py_ast.Continue):
        return PyContinue()
    elif isinstance(node, py_ast.Match):
        cases = []
        for c in node.cases:
            cases.append(
                PyMatchCase(
                    pattern=_convert_pattern(c.pattern),
                    guard=_convert_expr(c.guard) if c.guard else None,
                    body=[_convert_stmt(s) for s in c.body],
                )
            )
        return PyMatch(subject=_convert_expr(node.subject), cases=cases)
    elif isinstance(node, py_ast.Import):
        return PyImport(names=[alias.name for alias in node.names])
    elif isinstance(node, py_ast.ImportFrom):
        module = node.module or ""
        return PyImport(names=[f"{module}.{alias.name}" for alias in node.names])
    elif isinstance(node, py_ast.Raise):
        return PyRaise(exc=_convert_expr(node.exc))
    elif isinstance(node, py_ast.Try):
        return PyTry(
            body=[_convert_stmt(s) for s in node.body],
            handlers=[_convert_except_handler(h) for h in node.handlers],
            orelse=[_convert_stmt(s) for s in node.orelse] if node.orelse else [],
            finalbody=[_convert_stmt(s) for s in node.finalbody]
            if node.finalbody
            else [],
        )
    elif isinstance(node, py_ast.With):
        return PyWith(
            items=[_convert_withitem(item) for item in node.items],
            body=[_convert_stmt(s) for s in node.body],
        )
    elif isinstance(node, py_ast.AsyncWith):
        return PyAsyncWith(
            items=[_convert_withitem(item) for item in node.items],
            body=[_convert_stmt(s) for s in node.body],
        )
    elif isinstance(node, py_ast.Assert):
        return PyAssert(
            test=_convert_expr(node.test),
            msg=_convert_expr(node.msg) if node.msg else None,
        )
    elif isinstance(node, py_ast.Global):
        return PyGlobal(names=list(node.names))
    elif isinstance(node, py_ast.Nonlocal):
        return PyNonlocal(names=list(node.names))
    elif isinstance(node, py_ast.Delete):
        return PyDelete(targets=[_convert_expr(t) for t in node.targets])
    elif hasattr(py_ast, 'TypeAlias') and isinstance(node, py_ast.TypeAlias):
        return PyTypeAlias(
            name=_convert_expr(node.name),
            value=_convert_expr(node.value),
        )
    raise ValueError(f"Unknown statement: {type(node).__name__}")


def _convert_expr(node: py_ast.expr | None) -> PyExpr | None:
    if node is None:
        return None
    if isinstance(node, py_ast.Name):
        return PyName(id=node.id)
    elif isinstance(node, py_ast.Constant):
        kind = None
        if node.kind == "u":
            kind = "u"
        return PyConstant(value=node.value, kind=kind)
    elif isinstance(node, py_ast.BinOp):
        op = _BINOP_MAP.get(type(node.op), str(type(node.op).__name__))
        return PyBinOp(
            left=_convert_expr(node.left), op=op, right=_convert_expr(node.right)
        )
    elif isinstance(node, py_ast.UnaryOp):
        op = _UNARYOP_MAP.get(type(node.op), str(type(node.op).__name__))
        return PyUnaryOp(op=op, operand=_convert_expr(node.operand))
    elif isinstance(node, py_ast.Compare):
        ops = [_CMPOP_MAP.get(type(o), str(type(o).__name__)) for o in node.ops]
        return PyCompare(
            left=_convert_expr(node.left),
            ops=ops,
            comparators=[_convert_expr(c) for c in node.comparators],
        )
    elif isinstance(node, py_ast.BoolOp):
        op = _BOOLOP_MAP.get(type(node.op), str(type(node.op).__name__))
        return PyBoolOp(op=op, values=[_convert_expr(v) for v in node.values])
    elif isinstance(node, py_ast.Call):
        return PyCall(
            func=_convert_expr(node.func),
            args=[_convert_expr(a) for a in node.args],
            kwargs=[
                (kw.arg, _convert_expr(kw.value)) for kw in node.keywords if kw.arg
            ],
        )
    elif isinstance(node, py_ast.IfExp):
        return PyIfExp(
            test=_convert_expr(node.test),
            body=_convert_expr(node.body),
            orelse=_convert_expr(node.orelse),
        )
    elif isinstance(node, py_ast.Attribute):
        return PyAttribute(value=_convert_expr(node.value), attr=node.attr)
    elif isinstance(node, py_ast.Subscript):
        return PySubscript(
            value=_convert_expr(node.value), slice=_convert_expr(node.slice)
        )
    elif isinstance(node, py_ast.Slice):
        return PySlice(
            lower=_convert_expr(node.lower) if node.lower else None,
            upper=_convert_expr(node.upper) if node.upper else None,
            step=_convert_expr(node.step) if node.step else None,
        )
    elif isinstance(node, py_ast.List):
        return PyList(elts=[_convert_expr(e) for e in node.elts])
    elif isinstance(node, py_ast.Tuple):
        return PyTuple(elts=[_convert_expr(e) for e in node.elts])
    elif isinstance(node, py_ast.Set):
        return PySet(elts=[_convert_expr(e) for e in node.elts])
    elif isinstance(node, py_ast.Dict):
        return PyDict(
            keys=[_convert_expr(k) if k else None for k in node.keys],
            values=[_convert_expr(v) for v in node.values],
        )
    elif isinstance(node, py_ast.Lambda):
        return PyLambda(
            args=[
                (arg.arg, _convert_expr(arg.annotation) if arg.annotation else None)
                for arg in node.args.args
            ],
            body=_convert_expr(node.body),
        )
    elif isinstance(node, py_ast.ListComp):
        return PyListComp(
            elt=_convert_expr(node.elt),
            generators=[_convert_comprehension(g) for g in node.generators],
        )
    elif isinstance(node, py_ast.SetComp):
        return PySetComp(
            elt=_convert_expr(node.elt),
            generators=[_convert_comprehension(g) for g in node.generators],
        )
    elif isinstance(node, py_ast.DictComp):
        return PyDictComp(
            key=_convert_expr(node.key),
            value=_convert_expr(node.value),
            generators=[_convert_comprehension(g) for g in node.generators],
        )
    elif isinstance(node, py_ast.Starred):
        return PyStarred(value=_convert_expr(node.value))
    elif isinstance(node, py_ast.Await):
        return PyAwait(value=_convert_expr(node.value))
    elif isinstance(node, py_ast.Yield):
        return PyYield(value=_convert_expr(node.value) if node.value else None)
    elif isinstance(node, py_ast.YieldFrom):
        return PyYieldFrom(value=_convert_expr(node.value))
    elif isinstance(node, py_ast.NamedExpr):
        return PyWalrus(
            target=_convert_expr(node.target), value=_convert_expr(node.value)
        )
    elif isinstance(node, py_ast.NameConstant):
        return PyConstant(value=node.value)
    elif isinstance(node, py_ast.Num):
        return PyConstant(value=node.n)
    elif isinstance(node, py_ast.Str):
        return PyConstant(value=node.s)
    raise ValueError(f"Unknown expression: {type(node).__name__}")


def _convert_args(
    node: py_ast.arguments,
) -> list[tuple[str, PyExpr | None, PyExpr | None]]:
    args = []
    for arg in node.args:
        annotation = _convert_expr(arg.annotation) if arg.annotation else None
        args.append((arg.arg, annotation, None))
    if node.vararg:
        args.append(
            (
                "*" + node.vararg.arg,
                _convert_expr(node.vararg.annotation)
                if node.vararg.annotation
                else None,
                None,
            )
        )
    for arg in node.kwonlyargs:
        annotation = _convert_expr(arg.annotation) if arg.annotation else None
        args.append((arg.arg, annotation, None))
    if node.kwarg:
        args.append(
            (
                "**" + node.kwarg.arg,
                _convert_expr(node.kwarg.annotation) if node.kwarg.annotation else None,
                None,
            )
        )
    if node.defaults:
        for i, default in enumerate(node.defaults):
            idx = len(node.args) - len(node.defaults) + i
            if 0 <= idx < len(args):
                args[idx] = (args[idx][0], args[idx][1], _convert_expr(default))
    return args


def _convert_comprehension(node: py_ast.comprehension) -> PyComprehension:
    return PyComprehension(
        target=_convert_expr(node.target),
        iter=_convert_expr(node.iter),
        ifs=[_convert_expr(e) for e in node.ifs],
        is_async=bool(node.is_async),
    )


def _convert_pattern(node: py_ast.pattern) -> PyExpr:
    if isinstance(node, py_ast.MatchValue):
        return _convert_expr(node.value)
    elif isinstance(node, py_ast.MatchSingleton):
        return PyConstant(value=node.value)
    elif isinstance(node, py_ast.MatchAs):
        name = PyName(id=node.name) if node.name else PyName(id="_")
        if node.pattern:
            return _convert_pattern(node.pattern)
        return name
    elif isinstance(node, py_ast.MatchOr):
        patterns = [_convert_pattern(p) for p in node.patterns]
        return patterns[0]  # simplified
    raise ValueError(f"Unknown pattern: {type(node).__name__}")


def _convert_except_handler(node: py_ast.ExceptHandler) -> PyExceptHandler:
    return PyExceptHandler(
        typ=_convert_expr(node.type) if node.type else None,
        name=node.name,
        body=[_convert_stmt(s) for s in node.body],
    )


def _convert_withitem(node: py_ast.withitem) -> PyNode:
    return (
        _convert_expr(node.context_expr),
        _convert_expr(node.optional_vars) if node.optional_vars else None,
    )
