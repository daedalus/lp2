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


def _handle_FunctionDef(node: py_ast.stmt) -> PyStmt:
    n = node  # type: ignore[attr-defined]
    return PyFunctionDef(
        name=n.name,
        args=_convert_args(n.args),
        return_type=_convert_expr(n.returns) if n.returns else None,
        body=[_convert_stmt(s) for s in n.body],
        decorators=[_convert_expr(d) for d in n.decorator_list],
    )

def _handle_AsyncFunctionDef(node: py_ast.stmt) -> PyStmt:
    n = node  # type: ignore[attr-defined]
    return PyAsyncFunctionDef(
        name=n.name, args=_convert_args(n.args),
        return_type=_convert_expr(n.returns) if n.returns else None,
        body=[_convert_stmt(s) for s in n.body],
    )

def _handle_ClassDef(node: py_ast.stmt) -> PyStmt:
    n = node  # type: ignore[attr-defined]
    return PyClassDef(
        name=n.name, bases=[_convert_expr(b) for b in n.bases],
        body=[_convert_stmt(s) for s in n.body],
    )

def _handle_Return(node: py_ast.stmt) -> PyStmt:
    return PyReturn(value=_convert_expr(node.value) if node.value else None)

def _handle_Assign(node: py_ast.stmt) -> PyStmt:
    n = node  # type: ignore[attr-defined]
    targets = n.targets
    if len(targets) == 1:
        return PyAssign(target=_convert_expr(targets[0]), value=_convert_expr(n.value))
    return PyAssign(
        target=PyTuple(elts=[_convert_expr(t) for t in targets]),
        value=_convert_expr(n.value),
    )

def _handle_AnnAssign(node: py_ast.stmt) -> PyStmt:
    n = node  # type: ignore[attr-defined]
    return PyAnnAssign(
        target=_convert_expr(n.target), annotation=_convert_expr(n.annotation),
        value=_convert_expr(n.value) if n.value else None,
    )

def _handle_If(node: py_ast.stmt) -> PyStmt:
    n = node  # type: ignore[attr-defined]
    return PyIf(
        test=_convert_expr(n.test),
        body=[_convert_stmt(s) for s in n.body],
        orelse=[_convert_stmt(s) for s in n.orelse],
    )

def _handle_For(node: py_ast.stmt) -> PyStmt:
    n = node  # type: ignore[attr-defined]
    return PyFor(
        target=_convert_expr(n.target), iter=_convert_expr(n.iter),
        body=[_convert_stmt(s) for s in n.body],
    )

def _handle_AsyncFor(node: py_ast.stmt) -> PyStmt:
    n = node  # type: ignore[attr-defined]
    return PyAsyncFor(
        target=_convert_expr(n.target), iter=_convert_expr(n.iter),
        body=[_convert_stmt(s) for s in n.body],
    )

def _handle_While(node: py_ast.stmt) -> PyStmt:
    n = node  # type: ignore[attr-defined]
    return PyWhile(
        test=_convert_expr(n.test),
        body=[_convert_stmt(s) for s in n.body],
    )

def _handle_Expr(node: py_ast.stmt) -> PyStmt:
    return PyExprStmt(expr=_convert_expr(node.value))

def _handle_Pass(node: py_ast.stmt) -> PyStmt:
    return PyPass()

def _handle_Break(node: py_ast.stmt) -> PyStmt:
    return PyBreak()

def _handle_Continue(node: py_ast.stmt) -> PyStmt:
    return PyContinue()

def _handle_Match(node: py_ast.stmt) -> PyStmt:
    n = node  # type: ignore[attr-defined]
    cases = [
        PyMatchCase(
            pattern=_convert_pattern(c.pattern),
            guard=_convert_expr(c.guard) if c.guard else None,
            body=[_convert_stmt(s) for s in c.body],
        )
        for c in n.cases
    ]
    return PyMatch(subject=_convert_expr(n.subject), cases=cases)

def _handle_Import(node: py_ast.stmt) -> PyStmt:
    return PyImport(names=[alias.name for alias in node.names])

def _handle_ImportFrom(node: py_ast.stmt) -> PyStmt:
    module = node.module or ""
    return PyImport(names=[f"{module}.{alias.name}" for alias in node.names])

def _handle_Raise(node: py_ast.stmt) -> PyStmt:
    return PyRaise(exc=_convert_expr(node.exc))

def _handle_Try(node: py_ast.stmt) -> PyStmt:
    n = node  # type: ignore[attr-defined]
    return PyTry(
        body=[_convert_stmt(s) for s in n.body],
        handlers=[_convert_except_handler(h) for h in n.handlers],
        orelse=[_convert_stmt(s) for s in n.orelse] if n.orelse else [],
        finalbody=[_convert_stmt(s) for s in n.finalbody] if n.finalbody else [],
    )

def _handle_With(node: py_ast.stmt) -> PyStmt:
    n = node  # type: ignore[attr-defined]
    return PyWith(
        items=[_convert_withitem(item) for item in n.items],
        body=[_convert_stmt(s) for s in n.body],
    )

def _handle_AsyncWith(node: py_ast.stmt) -> PyStmt:
    n = node  # type: ignore[attr-defined]
    return PyAsyncWith(
        items=[_convert_withitem(item) for item in n.items],
        body=[_convert_stmt(s) for s in n.body],
    )

def _handle_Assert(node: py_ast.stmt) -> PyStmt:
    n = node  # type: ignore[attr-defined]
    return PyAssert(
        test=_convert_expr(n.test),
        msg=_convert_expr(n.msg) if n.msg else None,
    )

def _handle_Global(node: py_ast.stmt) -> PyStmt:
    return PyGlobal(names=list(node.names))

def _handle_Nonlocal(node: py_ast.stmt) -> PyStmt:
    return PyNonlocal(names=list(node.names))

def _handle_Delete(node: py_ast.stmt) -> PyStmt:
    return PyDelete(targets=[_convert_expr(t) for t in node.targets])

def _handle_TypeAlias(node: py_ast.stmt) -> PyStmt:
    return PyTypeAlias(
        name=_convert_expr(node.name),
        value=_convert_expr(node.value),
    )

_STMT_HANDLERS: dict[type, object] = {
    py_ast.FunctionDef: _handle_FunctionDef,
    py_ast.AsyncFunctionDef: _handle_AsyncFunctionDef,
    py_ast.ClassDef: _handle_ClassDef,
    py_ast.Return: _handle_Return,
    py_ast.Assign: _handle_Assign,
    py_ast.AnnAssign: _handle_AnnAssign,
    py_ast.If: _handle_If,
    py_ast.For: _handle_For,
    py_ast.AsyncFor: _handle_AsyncFor,
    py_ast.While: _handle_While,
    py_ast.Expr: _handle_Expr,
    py_ast.Pass: _handle_Pass,
    py_ast.Break: _handle_Break,
    py_ast.Continue: _handle_Continue,
    py_ast.Match: _handle_Match,
    py_ast.Import: _handle_Import,
    py_ast.ImportFrom: _handle_ImportFrom,
    py_ast.Raise: _handle_Raise,
    py_ast.Try: _handle_Try,
    py_ast.With: _handle_With,
    py_ast.AsyncWith: _handle_AsyncWith,
    py_ast.Assert: _handle_Assert,
    py_ast.Global: _handle_Global,
    py_ast.Nonlocal: _handle_Nonlocal,
    py_ast.Delete: _handle_Delete,
}
if hasattr(py_ast, "TypeAlias"):
    _STMT_HANDLERS[py_ast.TypeAlias] = _handle_TypeAlias

def _convert_stmt(node: py_ast.stmt) -> PyStmt:
    handler = _STMT_HANDLERS.get(type(node))
    if handler is not None:
        return handler(node)
    raise ValueError(f"Unknown statement: {type(node).__name__}")


def _cvt_Name(node: py_ast.expr) -> PyExpr:
    return PyName(id=node.id)

def _cvt_Constant(node: py_ast.expr) -> PyExpr:
    kind = "u" if node.kind == "u" else None
    return PyConstant(value=node.value, kind=kind)

def _cvt_BinOp(node: py_ast.expr) -> PyExpr:
    op = _BINOP_MAP.get(type(node.op), str(type(node.op).__name__))
    return PyBinOp(left=_convert_expr(node.left), op=op, right=_convert_expr(node.right))

def _cvt_UnaryOp(node: py_ast.expr) -> PyExpr:
    op = _UNARYOP_MAP.get(type(node.op), str(type(node.op).__name__))
    return PyUnaryOp(op=op, operand=_convert_expr(node.operand))

def _cvt_Compare(node: py_ast.expr) -> PyExpr:
    ops = [_CMPOP_MAP.get(type(o), str(type(o).__name__)) for o in node.ops]
    return PyCompare(
        left=_convert_expr(node.left), ops=ops,
        comparators=[_convert_expr(c) for c in node.comparators],
    )

def _cvt_BoolOp(node: py_ast.expr) -> PyExpr:
    op = _BOOLOP_MAP.get(type(node.op), str(type(node.op).__name__))
    return PyBoolOp(op=op, values=[_convert_expr(v) for v in node.values])

def _cvt_Call(node: py_ast.expr) -> PyExpr:
    return PyCall(
        func=_convert_expr(node.func),
        args=[_convert_expr(a) for a in node.args],
        kwargs=[(kw.arg, _convert_expr(kw.value)) for kw in node.keywords if kw.arg],
    )

def _cvt_IfExp(node: py_ast.expr) -> PyExpr:
    return PyIfExp(
        test=_convert_expr(node.test), body=_convert_expr(node.body),
        orelse=_convert_expr(node.orelse),
    )

def _cvt_Attribute(node: py_ast.expr) -> PyExpr:
    return PyAttribute(value=_convert_expr(node.value), attr=node.attr)

def _cvt_Subscript(node: py_ast.expr) -> PyExpr:
    return PySubscript(value=_convert_expr(node.value), slice=_convert_expr(node.slice))

def _cvt_Slice(node: py_ast.expr) -> PyExpr:
    return PySlice(
        lower=_convert_expr(node.lower) if node.lower else None,
        upper=_convert_expr(node.upper) if node.upper else None,
        step=_convert_expr(node.step) if node.step else None,
    )

def _cvt_List(node: py_ast.expr) -> PyExpr:
    return PyList(elts=[_convert_expr(e) for e in node.elts])

def _cvt_Tuple(node: py_ast.expr) -> PyExpr:
    return PyTuple(elts=[_convert_expr(e) for e in node.elts])

def _cvt_Set(node: py_ast.expr) -> PyExpr:
    return PySet(elts=[_convert_expr(e) for e in node.elts])

def _cvt_Dict(node: py_ast.expr) -> PyExpr:
    return PyDict(
        keys=[_convert_expr(k) if k else None for k in node.keys],
        values=[_convert_expr(v) for v in node.values],
    )

def _cvt_Lambda(node: py_ast.expr) -> PyExpr:
    return PyLambda(
        args=[(arg.arg, _convert_expr(arg.annotation) if arg.annotation else None)
              for arg in node.args.args],
        body=_convert_expr(node.body),
    )

def _cvt_ListComp(node: py_ast.expr) -> PyExpr:
    return PyListComp(
        elt=_convert_expr(node.elt),
        generators=[_convert_comprehension(g) for g in node.generators],
    )

def _cvt_SetComp(node: py_ast.expr) -> PyExpr:
    return PySetComp(
        elt=_convert_expr(node.elt),
        generators=[_convert_comprehension(g) for g in node.generators],
    )

def _cvt_DictComp(node: py_ast.expr) -> PyExpr:
    return PyDictComp(
        key=_convert_expr(node.key), value=_convert_expr(node.value),
        generators=[_convert_comprehension(g) for g in node.generators],
    )

def _cvt_Starred(node: py_ast.expr) -> PyExpr:
    return PyStarred(value=_convert_expr(node.value))

def _cvt_Await(node: py_ast.expr) -> PyExpr:
    return PyAwait(value=_convert_expr(node.value))

def _cvt_Yield(node: py_ast.expr) -> PyExpr:
    return PyYield(value=_convert_expr(node.value) if node.value else None)

def _cvt_YieldFrom(node: py_ast.expr) -> PyExpr:
    return PyYieldFrom(value=_convert_expr(node.value))

def _cvt_NamedExpr(node: py_ast.expr) -> PyExpr:
    return PyWalrus(target=_convert_expr(node.target), value=_convert_expr(node.value))

def _cvt_NameConstant(node: py_ast.expr) -> PyExpr:
    return PyConstant(value=node.value)

def _cvt_Num(node: py_ast.expr) -> PyExpr:
    return PyConstant(value=node.n)

def _cvt_Str(node: py_ast.expr) -> PyExpr:
    return PyConstant(value=node.s)

_EXPR_HANDLERS: dict[type, object] = {
    py_ast.Name: _cvt_Name,
    py_ast.Constant: _cvt_Constant,
    py_ast.BinOp: _cvt_BinOp,
    py_ast.UnaryOp: _cvt_UnaryOp,
    py_ast.Compare: _cvt_Compare,
    py_ast.BoolOp: _cvt_BoolOp,
    py_ast.Call: _cvt_Call,
    py_ast.IfExp: _cvt_IfExp,
    py_ast.Attribute: _cvt_Attribute,
    py_ast.Subscript: _cvt_Subscript,
    py_ast.Slice: _cvt_Slice,
    py_ast.List: _cvt_List,
    py_ast.Tuple: _cvt_Tuple,
    py_ast.Set: _cvt_Set,
    py_ast.Dict: _cvt_Dict,
    py_ast.Lambda: _cvt_Lambda,
    py_ast.ListComp: _cvt_ListComp,
    py_ast.SetComp: _cvt_SetComp,
    py_ast.DictComp: _cvt_DictComp,
    py_ast.Starred: _cvt_Starred,
    py_ast.Await: _cvt_Await,
    py_ast.Yield: _cvt_Yield,
    py_ast.YieldFrom: _cvt_YieldFrom,
    py_ast.NamedExpr: _cvt_NamedExpr,
    py_ast.NameConstant: _cvt_NameConstant,
    py_ast.Num: _cvt_Num,
    py_ast.Str: _cvt_Str,
}

def _convert_expr(node: py_ast.expr | None) -> PyExpr | None:
    if node is None:
        return None
    handler = _EXPR_HANDLERS.get(type(node))
    if handler is not None:
        return handler(node)
    raise ValueError(f"Unknown expression: {type(node).__name__}")


def _convert_vararg(node: py_ast.arguments, args: list) -> None:
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


def _convert_kwonlyargs(node: py_ast.arguments, args: list) -> None:
    for arg in node.kwonlyargs:
        annotation = _convert_expr(arg.annotation) if arg.annotation else None
        args.append((arg.arg, annotation, None))


def _convert_kwarg(node: py_ast.arguments, args: list) -> None:
    if node.kwarg:
        args.append(
            (
                "**" + node.kwarg.arg,
                _convert_expr(node.kwarg.annotation) if node.kwarg.annotation else None,
                None,
            )
        )


def _convert_args(
    node: py_ast.arguments,
) -> list[tuple[str, PyExpr | None, PyExpr | None]]:
    args = []
    for arg in node.args:
        annotation = _convert_expr(arg.annotation) if arg.annotation else None
        args.append((arg.arg, annotation, None))
    _convert_vararg(node, args)
    _convert_kwonlyargs(node, args)
    _convert_kwarg(node, args)
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
