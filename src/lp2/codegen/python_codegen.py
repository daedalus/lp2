from lp2.ast.python_ast import *


def generate_python(node: PyNode) -> str:
    if isinstance(node, PyModule):
        return _gen_module(node)
    raise ValueError(f"Unknown node: {type(node).__name__}")


def _gen_module(node: PyModule) -> str:
    lines = []
    for stmt in node.body:
        lines.append(_gen_stmt(stmt, 0))
    return "\n".join(lines) + "\n"


def _gen_stmt_FunctionDef(node: PyFunctionDef, indent: int) -> str:
    i = "    " * indent
    parts = [f"{i}def {node.name}("]
    arg_parts = []
    for arg_name, annotation, default in node.args:
        a = arg_name
        if annotation:
            a += f": {_gen_expr(annotation)}"
        if default is not None:
            a += f" = {_gen_expr(default)}"
        arg_parts.append(a)
    parts.append(", ".join(arg_parts))
    parts.append(")")
    if node.return_type:
        parts.append(f" -> {_gen_expr(node.return_type)}")
    parts.append(":")
    lines = ["".join(parts)]
    if not node.body:
        lines.append(f"{i}    pass")
    else:
        for s in node.body:
            lines.append(_gen_stmt(s, indent + 1))
    return "\n".join(lines)


def _gen_stmt_ClassDef(node: PyClassDef, indent: int) -> str:
    i = "    " * indent
    parts = [f"{i}class {node.name}"]
    if node.bases:
        parts.append(f"({', '.join(_gen_expr(b) for b in node.bases)})")
    parts.append(":")
    lines = ["".join(parts)]
    if not node.body:
        lines.append(f"{i}    pass")
    else:
        for s in node.body:
            lines.append(_gen_stmt(s, indent + 1))
    return "\n".join(lines)


def _gen_stmt_Return(node: PyReturn, indent: int) -> str:
    i = "    " * indent
    if node.value:
        return f"{i}return {_gen_expr(node.value)}"
    return f"{i}return"


def _gen_stmt_Assign(node: PyAssign, indent: int) -> str:
    i = "    " * indent
    return f"{i}{_gen_expr(node.target)} = {_gen_expr(node.value)}"


def _gen_stmt_AugAssign(node: PyAugAssign, indent: int) -> str:
    i = "    " * indent
    return f"{i}{_gen_expr(node.target)} {node.op}= {_gen_expr(node.value)}"


def _gen_stmt_AnnAssign(node: PyAnnAssign, indent: int) -> str:
    i = "    " * indent
    if node.value:
        return f"{i}{_gen_expr(node.target)}: {_gen_expr(node.annotation)} = {_gen_expr(node.value)}"
    return f"{i}{_gen_expr(node.target)}: {_gen_expr(node.annotation)}"


def _gen_stmt_If(node: PyIf, indent: int) -> str:
    i = "    " * indent
    lines = [f"{i}if {_gen_expr(node.test)}:"]
    if not node.body:
        lines.append(f"{i}    pass")
    else:
        for s in node.body:
            lines.append(_gen_stmt(s, indent + 1))
    if node.orelse:
        if len(node.orelse) == 1 and isinstance(node.orelse[0], PyIf):
            lines.append(f"{i}elif {_gen_expr(node.orelse[0].test)}:")
            for s in node.orelse[0].body:
                lines.append(_gen_stmt(s, indent + 1))
            if node.orelse[0].orelse:
                _append_else(lines, node.orelse[0].orelse, indent, i)
        else:
            lines.append(f"{i}else:")
            for s in node.orelse:
                lines.append(_gen_stmt(s, indent + 1))
    return "\n".join(lines)


def _gen_stmt_For(node: PyFor, indent: int) -> str:
    i = "    " * indent
    lines = [f"{i}for {_gen_expr(node.target)} in {_gen_expr(node.iter)}:"]
    if not node.body:
        lines.append(f"{i}    pass")
    else:
        for s in node.body:
            lines.append(_gen_stmt(s, indent + 1))
    return "\n".join(lines)


def _gen_stmt_While(node: PyWhile, indent: int) -> str:
    i = "    " * indent
    lines = [f"{i}while {_gen_expr(node.test)}:"]
    if not node.body:
        lines.append(f"{i}    pass")
    else:
        for s in node.body:
            lines.append(_gen_stmt(s, indent + 1))
    return "\n".join(lines)


def _gen_stmt_Expr(node: PyExprStmt, indent: int) -> str:
    i = "    " * indent
    return f"{i}{_gen_expr(node.expr)}"


def _gen_stmt_Pass(node: PyPass, indent: int) -> str:
    i = "    " * indent
    return f"{i}pass"


def _gen_stmt_Break(node: PyBreak, indent: int) -> str:
    i = "    " * indent
    return f"{i}break"


def _gen_stmt_Continue(node: PyContinue, indent: int) -> str:
    i = "    " * indent
    return f"{i}continue"


def _gen_stmt_Import(node: PyImport, indent: int) -> str:
    i = "    " * indent
    # Split into regular imports and from-imports
    regular = []
    from_imports: dict[str, list[str]] = {}
    for name in node.names:
        if "." in name:
            module, _, attr = name.partition(".")
            from_imports.setdefault(module, []).append(attr)
        else:
            regular.append(name)
    parts = []
    if regular:
        parts.append(f"{i}import {', '.join(regular)}")
    for module, attrs in from_imports.items():
        parts.append(f"{i}from {module} import {', '.join(attrs)}")
    return "\n".join(parts)


def _gen_stmt_Raise(node: PyRaise, indent: int) -> str:
    i = "    " * indent
    if node.exc is None:
        return f"{i}raise"
    return f"{i}raise {_gen_expr(node.exc)}"


def _gen_stmt_Try(node: PyTry, indent: int) -> str:
    i = "    " * indent
    lines = [f"{i}try:"]
    for s in node.body:
        lines.append(_gen_stmt(s, indent + 1))
    for handler in node.handlers:
        lines.append(_gen_except_handler(handler, indent, i))
    if node.orelse:
        lines.append(f"{i}else:")
        for s in node.orelse:
            lines.append(_gen_stmt(s, indent + 1))
    if node.finalbody:
        lines.append(f"{i}finally:")
        for s in node.finalbody:
            lines.append(_gen_stmt(s, indent + 1))
    return "\n".join(lines)


def _gen_stmt_With(node: PyWith, indent: int) -> str:
    i = "    " * indent
    items = ", ".join(
        f"{_gen_expr(item[0])}" + (f" as {_gen_expr(item[1])}" if item[1] else "")
        for item in node.items
    )
    lines = [f"{i}with {items}:"]
    for s in node.body:
        lines.append(_gen_stmt(s, indent + 1))
    return "\n".join(lines)


def _gen_stmt_Assert(node: PyAssert, indent: int) -> str:
    i = "    " * indent
    if node.msg:
        return f"{i}assert {_gen_expr(node.test)}, {_gen_expr(node.msg)}"
    return f"{i}assert {_gen_expr(node.test)}"


def _gen_stmt_Global(node: PyGlobal, indent: int) -> str:
    i = "    " * indent
    return f"{i}global {', '.join(node.names)}"


def _gen_stmt_Nonlocal(node: PyNonlocal, indent: int) -> str:
    i = "    " * indent
    return f"{i}nonlocal {', '.join(node.names)}"


def _gen_stmt_Delete(node: PyDelete, indent: int) -> str:
    i = "    " * indent
    return f"{i}del {', '.join(_gen_expr(t) for t in node.targets)}"


def _gen_stmt_Match(node: PyMatch, indent: int) -> str:
    i = "    " * indent
    lines = [f"{i}match {_gen_expr(node.subject)}:"]
    for case in node.cases:
        guard_str = f" if {_gen_expr(case.guard)}" if case.guard else ""
        lines.append(f"{i}    case {_gen_pattern_py(case.pattern)}{guard_str}:")
        if not case.body:
            lines.append(f"{i}        pass")
        else:
            for s in case.body:
                lines.append(_gen_stmt(s, indent + 2))
    return "\n".join(lines)


def _gen_stmt_TypeAlias(node: PyTypeAlias, indent: int) -> str:
    i = "    " * indent
    return f"{i}type {_gen_expr(node.name)} = {_gen_expr(node.value)}"


_STMT_GEN = {
    PyFunctionDef: _gen_stmt_FunctionDef,
    PyClassDef: _gen_stmt_ClassDef,
    PyReturn: _gen_stmt_Return,
    PyAssign: _gen_stmt_Assign,
    PyAugAssign: _gen_stmt_AugAssign,
    PyAnnAssign: _gen_stmt_AnnAssign,
    PyIf: _gen_stmt_If,
    PyFor: _gen_stmt_For,
    PyWhile: _gen_stmt_While,
    PyExprStmt: _gen_stmt_Expr,
    PyPass: _gen_stmt_Pass,
    PyBreak: _gen_stmt_Break,
    PyContinue: _gen_stmt_Continue,
    PyImport: _gen_stmt_Import,
    PyRaise: _gen_stmt_Raise,
    PyTry: _gen_stmt_Try,
    PyWith: _gen_stmt_With,
    PyAssert: _gen_stmt_Assert,
    PyGlobal: _gen_stmt_Global,
    PyNonlocal: _gen_stmt_Nonlocal,
    PyDelete: _gen_stmt_Delete,
    PyMatch: _gen_stmt_Match,
    PyTypeAlias: _gen_stmt_TypeAlias,
}


def _gen_stmt(node: PyNode, indent: int = 0) -> str:
    handler = _STMT_GEN.get(type(node))
    if handler is not None:
        return handler(node, indent)
    raise ValueError(f"Unknown statement: {type(node).__name__}")


def _append_else(lines, orelse, indent, i):
    if len(orelse) == 1 and isinstance(orelse[0], PyIf):
        lines.append(f"{i}elif {_gen_expr(orelse[0].test)}:")
        for s in orelse[0].body:
            lines.append(_gen_stmt(s, indent + 1))
        if orelse[0].orelse:
            _append_else(lines, orelse[0].orelse, indent, i)
    else:
        lines.append(f"{i}else:")
        for s in orelse:
            lines.append(_gen_stmt(s, indent + 1))


def _gen_except_handler(node: PyExceptHandler, indent: int, i: str) -> str:
    parts = [f"{i}except"]
    if node.typ:
        parts.append(f" {_gen_expr(node.typ)}")
    if node.name:
        parts.append(f" as {node.name}")
    parts.append(":")
    lines = ["".join(parts)]
    for s in node.body:
        lines.append(_gen_stmt(s, indent + 1))
    return "\n".join(lines)


def _gen_expr_Name(node: PyName, indent: int = 0) -> str:
    return node.id


def _gen_expr_Constant(node: PyConstant, indent: int = 0) -> str:
    if node.value is None:
        return "None"
    if isinstance(node.value, bool):
        return "True" if node.value else "False"
    if isinstance(node.value, str):
        return repr(node.value)
    if isinstance(node.value, bytes):
        return repr(node.value)
    return str(node.value)


_PY_BINOP_PREC: dict[str, int] = {
    "or": 1,
    "and": 2,
    "+": 5,
    "-": 5,
    "*": 6,
    "/": 6,
    "//": 6,
    "%": 6,
    "**": 7,
}


def _py_binop_prec(op: str) -> int:
    return _PY_BINOP_PREC.get(op, 4)


def _gen_py_binop_operand(node: PyExpr, parent_op: str, is_right: bool) -> str:
    if isinstance(node, PyBinOp):
        child_prec = _py_binop_prec(node.op)
        parent_prec = _py_binop_prec(parent_op)
        if child_prec < parent_prec or (is_right and child_prec == parent_prec):
            return f"({_gen_expr_BinOp(node)})"
    return _gen_expr(node)


def _gen_expr_BinOp(node: PyBinOp, indent: int = 0) -> str:
    left = _gen_py_binop_operand(node.left, node.op, is_right=False)
    right = _gen_py_binop_operand(node.right, node.op, is_right=True)
    return f"{left} {node.op} {right}"


def _gen_expr_UnaryOp(node: PyUnaryOp, indent: int = 0) -> str:
    operand = _gen_expr(node.operand)
    sep = " " if node.op.isalpha() else ""
    return f"{node.op}{sep}{operand}"


def _gen_expr_Compare(node: PyCompare, indent: int = 0) -> str:
    parts = [_gen_expr(node.left)]
    for i, op in enumerate(node.ops):
        parts.append(f" {op} {_gen_expr(node.comparators[i])}")
    return "".join(parts)


def _gen_expr_BoolOp(node: PyBoolOp, indent: int = 0) -> str:
    return f"{f' {node.op} '.join(_gen_expr(v) for v in node.values)}"


def _gen_expr_Call(node: PyCall, indent: int = 0) -> str:
    args = [_gen_expr(a) for a in node.args]
    kwargs = [f"{k}={_gen_expr(v)}" for k, v in node.kwargs]
    return f"{_gen_expr(node.func)}({', '.join(args + kwargs)})"


def _gen_expr_IfExp(node: PyIfExp, indent: int = 0) -> str:
    return f"{_gen_expr(node.body)} if {_gen_expr(node.test)} else {_gen_expr(node.orelse)}"


def _gen_expr_Attribute(node: PyAttribute, indent: int = 0) -> str:
    return f"{_gen_expr(node.value)}.{node.attr}"


def _gen_expr_Subscript(node: PySubscript, indent: int = 0) -> str:
    return f"{_gen_expr(node.value)}[{_gen_expr(node.slice)}]"


def _gen_expr_Slice(node: PySlice, indent: int = 0) -> str:
    parts = [
        _gen_expr(node.lower) if node.lower else "",
        ":" + (_gen_expr(node.upper) if node.upper else ""),
    ]
    if node.step:
        parts.append(f":{_gen_expr(node.step)}")
    return "".join(parts)


def _gen_expr_List(node: PyList, indent: int = 0) -> str:
    return f"[{', '.join(_gen_expr(e) for e in node.elts)}]"


def _gen_expr_Tuple(node: PyTuple, indent: int = 0) -> str:
    if len(node.elts) == 1:
        return f"({_gen_expr(node.elts[0])},)"
    return f"({', '.join(_gen_expr(e) for e in node.elts)})"


def _gen_expr_Set(node: PySet, indent: int = 0) -> str:
    return f"{{{', '.join(_gen_expr(e) for e in node.elts)}}}"


def _gen_expr_Dict(node: PyDict, indent: int = 0) -> str:
    items = []
    for k, v in zip(node.keys, node.values):
        k_str = _gen_expr(k) if k else ""
        items.append(f"{k_str}: {_gen_expr(v)}")
    return f"{{{', '.join(items)}}}"


def _gen_expr_Lambda(node: PyLambda, indent: int = 0) -> str:
    args = []
    for arg_name, annotation in node.args:
        a = arg_name
        if annotation:
            a += f": {_gen_expr(annotation)}"
        args.append(a)
    return f"lambda {', '.join(args)}: {_gen_expr(node.body)}"


def _gen_expr_ListComp(node: PyListComp, indent: int = 0) -> str:
    return f"[{_gen_expr(node.elt)} {_gen_comp_generators(node.generators)}]"


def _gen_expr_SetComp(node: PySetComp, indent: int = 0) -> str:
    return f"{{{_gen_expr(node.elt)} {_gen_comp_generators(node.generators)}}}"


def _gen_expr_DictComp(node: PyDictComp, indent: int = 0) -> str:
    return f"{{{_gen_expr(node.key)}: {_gen_expr(node.value)} {_gen_comp_generators(node.generators)}}}"


def _gen_expr_Starred(node: PyStarred, indent: int = 0) -> str:
    return f"*{_gen_expr(node.value)}"


def _gen_expr_Await(node: PyAwait, indent: int = 0) -> str:
    return f"await {_gen_expr(node.value)}"


def _gen_expr_Yield(node: PyYield, indent: int = 0) -> str:
    if node.value:
        return f"yield {_gen_expr(node.value)}"
    return "yield"


def _gen_expr_YieldFrom(node: PyYieldFrom, indent: int = 0) -> str:
    return f"yield from {_gen_expr(node.value)}"


def _gen_expr_Walrus(node: PyWalrus, indent: int = 0) -> str:
    return f"{_gen_expr(node.target)} := {_gen_expr(node.value)}"


def _gen_expr_Match(node: PyMatch, indent: int = 0) -> str:
    return f"match {_gen_expr(node.subject)}"


def _gen_expr_MatchCase(node: PyMatchCase, indent: int = 0) -> str:
    return f"case {_gen_pattern_py(node.pattern)}"


_EXPR_GEN = {
    PyName: _gen_expr_Name,
    PyConstant: _gen_expr_Constant,
    PyBinOp: _gen_expr_BinOp,
    PyUnaryOp: _gen_expr_UnaryOp,
    PyCompare: _gen_expr_Compare,
    PyBoolOp: _gen_expr_BoolOp,
    PyCall: _gen_expr_Call,
    PyIfExp: _gen_expr_IfExp,
    PyAttribute: _gen_expr_Attribute,
    PySubscript: _gen_expr_Subscript,
    PySlice: _gen_expr_Slice,
    PyList: _gen_expr_List,
    PyTuple: _gen_expr_Tuple,
    PySet: _gen_expr_Set,
    PyDict: _gen_expr_Dict,
    PyLambda: _gen_expr_Lambda,
    PyListComp: _gen_expr_ListComp,
    PySetComp: _gen_expr_SetComp,
    PyDictComp: _gen_expr_DictComp,
    PyStarred: _gen_expr_Starred,
    PyAwait: _gen_expr_Await,
    PyYield: _gen_expr_Yield,
    PyYieldFrom: _gen_expr_YieldFrom,
    PyWalrus: _gen_expr_Walrus,
    PyMatch: _gen_expr_Match,
    PyMatchCase: _gen_expr_MatchCase,
}


def _gen_expr(node: PyExpr) -> str:
    if node is None:
        return "None"
    handler = _EXPR_GEN.get(type(node))
    if handler is not None:
        return handler(node)
    raise ValueError(f"Unknown expression: {type(node).__name__}")


def _gen_pattern_py(node: PyExpr) -> str:
    if isinstance(node, PyName):
        return node.id
    if isinstance(node, PyConstant):
        if isinstance(node.value, bool):
            return "True" if node.value else "False"
        if node.value is None:
            return "None"
        return repr(node.value)
    if isinstance(node, PyMatchOr):
        return " | ".join(_gen_pattern_py(p) for p in node.patterns)
    return _gen_expr(node)


def _gen_comp_generators(generators: list[PyComprehension]) -> str:
    parts = []
    for g in generators:
        async_prefix = "async " if g.is_async else ""
        ifs = "".join(f" if {_gen_expr(if_clause)}" for if_clause in g.ifs)
        parts.append(
            f"{async_prefix}for {_gen_expr(g.target)} in {_gen_expr(g.iter)}{ifs}"
        )
    return " ".join(parts)
