import keyword

from lp2.ast.lean4_ast import *
from lp2.ast.python_ast import *


def _sanitize_identifier(name: str) -> str:
    result = "".join(
        c if c.isascii() and (c.isalnum() or c == "_") else "_" for c in name
    )
    if (
        not result
        or not result.isidentifier()
        or result[0].isdigit()
        or keyword.iskeyword(result)
    ):
        result = "_" + result
    return result


def _dedup_names(names: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    result: list[str] = []
    for n in names:
        clean = _sanitize_identifier(n)
        if clean in seen:
            seen[clean] += 1
            clean = f"{clean}_{seen[clean]}"
        else:
            seen[clean] = 0
        result.append(clean)
    return result


_LEAN_TYPE_TO_PY = {
    "Int": PyName("int"),
    "Nat": PyName("int"),
    "ℕ": PyName("int"),
    "ℤ": PyName("int"),
    "ℚ": PyName("float"),
    "ℝ": PyName("float"),
    "ℂ": PyName("complex"),
    "Float": PyName("float"),
    "Bool": PyName("bool"),
    "String": PyName("str"),
    "Char": PyName("str"),
    "Unit": PyName("None"),
    "List": PyName("list"),
    "Option": PyName("Optional"),
    "Prod": PyName("tuple"),
    "HashMap": PyName("dict"),
    "Set": PyName("set"),
}


def _cmd_to_stmts(node: LeanCommand) -> list[PyStmt]:
    """Convert a command to zero or more Python statements.

    Handles sections and namespaces by inlining their children
    (directory structure replaces the namespace wrapping).
    """
    if isinstance(node, (LeanSection, LeanNamespace)):
        result: list[PyStmt] = []
        for c in node.commands:
            result.extend(_cmd_to_stmts(c))
        return result
    stmt = _cmd_to_stmt(node)
    return [stmt] if stmt is not None else []


def lean_to_py(node: LeanNode) -> PyNode:
    if isinstance(node, LeanModule):
        body = []
        for cmd in node.body:
            body.extend(_cmd_to_stmts(cmd))
        # Prepend typing imports for Any/Optional fallback type annotations
        body.insert(0, PyImport(names=["typing.Any", "typing.Optional"]))
        return PyModule(body=body)
    raise ValueError(f"Unknown node: {type(node).__name__}")


# ---------------------------------------------------------------------------
# _cmd_to_stmt  dispatch
# ---------------------------------------------------------------------------


def _cmd_to_stmt_ns(n: LeanNamespace) -> PyStmt | None:
    stmts = []
    for c in n.commands:
        stmts.extend(_cmd_to_stmts(c))
    return PyClassDef(name=_sanitize_identifier(n.name), bases=[], body=stmts)


_CMD_TO_STMT = {
    LeanDef: lambda n: _def_to_func(n),
    LeanStructure: lambda n: _structure_to_class(n),
    LeanClass: lambda n: _structure_to_class(n),
    LeanInductive: lambda n: _inductive_to_class(n),
    LeanAxiom: lambda _: PyPass(),
    LeanExample: lambda n: (
        PyExprStmt(
            expr=PyCall(
                func=PyName("print"),
                args=[_expr_to_py(n.expr)],
            )
        )
        if n.expr
        else None
    ),

    LeanOpen: lambda n: PyImport(
        names=[_sanitize_identifier(name) for name in n.names]
    ),
    LeanVariable: lambda _: None,
    LeanNamespace: _cmd_to_stmt_ns,
}


def _cmd_to_stmt(node: LeanCommand) -> PyStmt | None:
    handler = _CMD_TO_STMT.get(type(node))
    if handler:
        return handler(node)
    return None


def _def_to_func(node: LeanDef) -> PyFunctionDef:
    name = _sanitize_identifier(node.name)
    py_args_raw = []

    for p in node.params:
        py_ann = _lean_type_to_py(p.type) if p.type else None
        py_default = _expr_to_py(p.default) if p.default else None
        py_args_raw.append((p.name, py_ann, py_default))

    existing_names = {p.name for p in node.params}
    return_type_expr = node.return_type
    while isinstance(return_type_expr, LeanForall):
        for fp in return_type_expr.params:
            if fp.name not in existing_names:
                py_ann = _lean_type_to_py(fp.type) if fp.type else None
                py_args_raw.append((fp.name, py_ann, None))
                existing_names.add(fp.name)
        return_type_expr = return_type_expr.body

    deduped = _dedup_names([r[0] for r in py_args_raw])
    py_args = [(deduped[i], r[1], r[2]) for i, r in enumerate(py_args_raw)]

    # For theorems/lemmas, use the statement (return type) as the body.
    # Regular defs use the value expression as body.
    if node.is_theorem or node.is_lemma:
        if return_type_expr:
            body = _expr_to_stmts(return_type_expr)
        else:
            body = [PyPass()]
        py_return = PyName("bool") if return_type_expr else None
    elif node.value and isinstance(node.value, LeanBy) and return_type_expr:
        body = _expr_to_stmts(return_type_expr)
        py_return = PyName("bool")
    else:
        py_return = _lean_type_to_py(return_type_expr) if return_type_expr else None
        body = _expr_to_stmts(node.value) if node.value else [PyPass()]

    if (
        py_return == PyName("None")
        or isinstance(py_return, PyName)
        and py_return.id == "None"
    ):
        body = _ensure_return(body)

    return PyFunctionDef(
        name=name, args=py_args, return_type=py_return, body=body, decorators=[]
    )


def _structure_to_class(node: LeanStructure) -> PyClassDef:
    body = []
    for field in node.fields:
        py_ann = _lean_type_to_py(field.type) if field.type else None
        field_name = _sanitize_identifier(field.name)
        if py_ann:
            body.append(
                PyAnnAssign(
                    target=PyName(field_name),
                    annotation=py_ann,
                    value=None,
                )
            )
        else:
            body.append(
                PyAssign(
                    target=PyName(field_name),
                    value=PyConstant(None),
                )
            )
    return PyClassDef(
        name=_sanitize_identifier(node.name), bases=[], body=body or [PyPass()]
    )


def _inductive_to_class(node: LeanInductive) -> PyClassDef:
    ctors = []
    for ctor in node.constructors:
        field_types = []
        for f in ctor.fields:
            field_types.append(_lean_type_to_py(f.type) if f.type else PyName("Any"))
        ctors.append((ctor.name, field_types))
    body = [PyPass()]
    return PyClassDef(name=_sanitize_identifier(node.name), bases=[], body=body)


def _ensure_return(stmts: list[PyStmt]) -> list[PyStmt]:
    if not stmts:
        return [PyReturn(value=None)]
    if isinstance(stmts[-1], PyReturn):
        return stmts
    if isinstance(stmts[-1], PyExprStmt):
        stmts = stmts[:-1] + [PyReturn(value=stmts[-1].expr)]
        return stmts
    return stmts


# ---------------------------------------------------------------------------
# _expr_to_stmts  dispatch
# ---------------------------------------------------------------------------


def _estmts_let(n: LeanLet) -> list[PyStmt]:
    if n.is_rec and n.params:
        inner = _expr_to_stmts(n.body)
        raw_names = [p.name for p in n.params]
        clean_names = _dedup_names(raw_names)
        params = [(clean_names[i], None, None) for i, p in enumerate(n.params)]
        func_body = _expr_to_stmts(n.value)
        return [
            PyFunctionDef(
                name=_sanitize_identifier(n.name),
                args=params,
                return_type=None,
                body=func_body,
            )
        ] + inner
    inner = _expr_to_stmts(n.body)
    val = _expr_to_py(n.value)
    return [PyAssign(target=PyName(_sanitize_identifier(n.name)), value=val)] + inner


def _estmts_have(n: LeanHave) -> list[PyStmt]:
    inner = _expr_to_stmts(n.body)
    val = _expr_to_py(n.value)
    return [
        PyAssign(target=PyName(_sanitize_identifier(n.name or "_")), value=val)
    ] + inner


def _estmts_if(n: LeanIf) -> list[PyStmt]:
    test = _expr_to_py(n.cond)
    then_stmts = _expr_to_stmts(n.then_expr)
    else_stmts = _expr_to_stmts(n.else_expr) if n.else_expr else []
    return [PyIf(test=test, body=then_stmts, orelse=else_stmts)]


def _estmts_match(n: LeanMatch) -> list[PyStmt]:
    subject = _expr_to_py(n.expr)
    cases = []
    guard_counter = 0
    for arm in n.arms:
        pat = arm.pattern
        body = _expr_to_stmts(arm.rhs)
        if not body:
            body = [PyPass()]
        # Bare names in Python match/case are capture variables, not constant
        # patterns. Use guards for constructors parsed as LeanPatternIdent
        # or empty-arity LeanPatternCtor (except known Python constants).
        ctor_name = None
        if isinstance(pat, LeanPatternCtor):
            ctor_name = _sanitize_identifier(pat.name)
        elif isinstance(pat, LeanPatternIdent):
            ctor_name = _sanitize_identifier(pat.name)
        if ctor_name:
            if ctor_name == "none":
                cases.append(PyMatchCase(pattern=PyName("None"), guard=None, body=body))
            elif ctor_name in ("true", "false"):
                cases.append(
                    PyMatchCase(
                        pattern=PyConstant(value=ctor_name == "true"),
                        guard=None,
                        body=body,
                    )
                )
            else:
                gv = f"_c{guard_counter}"
                guard_counter += 1
                gd = PyCompare(
                    left=PyName(gv), ops=["=="], comparators=[PyName(id=ctor_name)]
                )
                cases.append(PyMatchCase(pattern=PyName(gv), guard=gd, body=body))
        else:
            pat_expr = _pattern_to_expr(pat)
            cases.append(PyMatchCase(pattern=pat_expr, guard=None, body=body))
    if not cases:
        return [PyPass()]
    return [PyMatch(subject=subject, cases=cases)]


_EXPR_TO_STMTS = {
    LeanLet: _estmts_let,
    LeanHave: _estmts_have,
    LeanIf: _estmts_if,
    LeanMatch: _estmts_match,
    LeanLambda: lambda n: [PyReturn(value=_expr_to_py(n))],
    LeanUnit: lambda _: [PyReturn(value=None)],
}


def _expr_to_stmts(node: LeanExpr) -> list[PyStmt]:
    if (
        isinstance(node, LeanApp)
        and isinstance(node.func, LeanApp)
        and isinstance(node.func.func, LeanIdent)
        and node.func.func.name == "for_in"
    ):
        return [
            PyFor(
                target=PyName("_"),
                iter=_expr_to_py(node.func.arg),
                body=_expr_to_stmts(node.arg),
            )
        ]

    handler = _EXPR_TO_STMTS.get(type(node))
    if handler:
        return handler(node)

    py_expr = _expr_to_py(node)
    if isinstance(py_expr, PyName) and py_expr.id == "true":
        return [PyReturn(value=PyConstant(True))]
    if isinstance(py_expr, PyName) and py_expr.id == "false":
        return [PyReturn(value=PyConstant(False))]
    return [PyReturn(value=py_expr)]


def _collect_app_args(node: LeanApp) -> tuple[list[LeanExpr], LeanExpr]:
    args = []
    current = node
    while isinstance(current, LeanApp):
        func = current.func
        arg = current.arg
        if isinstance(func, LeanIdent) and func.name in ("List.cons", "Prod.mk"):
            break
        if (
            isinstance(func, LeanApp)
            and isinstance(func.func, LeanIdent)
            and func.func.name == "Prod.mk"
        ):
            break
        args.insert(0, arg)
        if isinstance(func, LeanApp):
            current = func
        else:
            return args, func
    return args, current


# ---------------------------------------------------------------------------
# _expr_to_py  dispatch
# ---------------------------------------------------------------------------


def _expr_py_ident(n: LeanIdent) -> PyExpr:
    if n.name == "none":
        return PyConstant(None)
    if n.name == "true":
        return PyConstant(True)
    if n.name == "false":
        return PyConstant(False)
    return PyName(id=_sanitize_identifier(n.name))


def _expr_py_app(n: LeanApp) -> PyExpr:
    if isinstance(n.func, LeanIdent) and n.func.name == "List.cons":
        if isinstance(n.arg, LeanListLit):
            return PyList(elts=[_expr_to_py(e) for e in n.arg.elts])
        if isinstance(n.arg, LeanIdent) and n.arg.name == "List.nil":
            return PyList(elts=[_expr_to_py(n.func)])
        return PyList(elts=[_expr_to_py(n.func), _expr_to_py(n.arg)])
    if (
        isinstance(n.func, LeanApp)
        and isinstance(n.func.func, LeanIdent)
        and n.func.func.name == "Prod.mk"
    ):
        left = _expr_to_py(n.func.arg)
        right = _expr_to_py(n.arg)
        if isinstance(left, PyTuple):
            return PyTuple(elts=left.elts + [right])
        return PyTuple(elts=[left, right])
    args, func = _collect_app_args(n)
    return PyCall(
        func=_expr_to_py(func), args=[_expr_to_py(a) for a in args], kwargs=[]
    )


_OP_MAP = {
    "+": "+",
    "-": "-",
    "*": "*",
    "/": "//",
    "%": "%",
    "=": "==",
    "==": "==",
    "!=": "!=",
    "≠": "!=",
    "<": "<",
    ">": ">",
    "<=": "<=",
    ">=": ">=",
    "≤": "<=",
    "≥": ">=",
    "&&": "and",
    "||": "or",
    "∧": "and",
    "∨": "or",
    "↔": "==",
    "::": "::",
    "|>": "|>",
    "^": "^",
    "++": "+",
    "∈": "in",
    "∉": "not_in",
    "⊆": "issubset",
    "⊇": "issuperset",
    "⊂": "issubset",
    "⊃": "issuperset",
    "∪": "|",
    "∩": "&",
    "∖": "-",
    "×": "*",
    "⊓": "meet",
    "⊔": "join",
    "⊤": "top",
    "⊥": "bot",
    "∘": "compose",
    "⊗": "tensor",
    "⊕": "oplus",
    "⊞": "oplus",
    "⊡": "boxdot",
    "⊚": "circ",
    "⊛": "ast",
    "⊠": "boxtimes",
    "∗": "*",
    "⋆": "*",
    "⨯": "*",
    "∥": "parallel",
    "†": "dagger",
    "•": "bullet",
    "·": "cdot",
    "′": "prime",
    "∇": "nabla",
    "∂": "partial",
    "∑": "sum",
    "∏": "prod",
    "∫": "integral",
    "√": "sqrt",
    "∞": "inf",
    "⌊": "floor",
    "⌈": "ceil",
    "⌋": "rfloor",
    "⌉": "rceil",
    "◁": "triangleleft",
    "▷": "triangleright",
    "⋈": "bowtie",
    "⋊": "rtimes",
    "⋉": "ltimes",
    "⋀": "big_and",
    "⋁": "big_or",
    "⋂": "big_inter",
    "⋃": "big_union",
    "⨁": "big_oplus",
    "⨂": "big_otimes",
    "⨿": "coproduct",
    "⋄": "diamond",
    "△": "triangle",
    "◻": "square",
    "◾": "square",
    "□": "square",
    "✶": "star",
    "⬝": "dot",
    "∙": "bullet",
    "⋮": "vellip",
    "⋯": "cdots",
}

_UNARY_OP_MAP = {
    "¬": "not",
    "-": "-",
    "+": "+",
    "~": "~",
    "not": "not",
}


_PY_BINOPS = frozenset(
    {
        "+",
        "-",
        "*",
        "/",
        "%",
        "**",
        "//",
        "<<",
        ">>",
        "&",
        "|",
        "^",
        "@",
        "==",
        "!=",
        "<",
        ">",
        "<=",
        ">=",
        "in",
        "and",
        "or",
        "is",
    }
)


def _expr_py_binop(n: LeanBinOp) -> PyExpr:
    left = _expr_to_py(n.left)
    right = _expr_to_py(n.right)
    if n.op == ">>=":
        return PyCall(func=PyName("bind"), args=[left, right], kwargs=[])
    if n.op == "|>":
        return PyCall(func=right, args=[left], kwargs=[])
    py_op = _OP_MAP.get(n.op)
    if py_op is not None:
        if py_op == "::":
            if isinstance(right, PyList):
                return PyList(elts=[left] + right.elts)
            return PyList(elts=[left, right])
        if py_op == "not_in":
            return PyCall(func=PyName("not_in"), args=[left, right], kwargs=[])
        if py_op in _PY_BINOPS:
            return PyBinOp(left=left, op=py_op, right=right)
        return PyCall(func=PyName(py_op), args=[left, right], kwargs=[])
    # Flat Unicode operator as function call
    op_name = f"op_{'_'.join(f'u{ord(c):04X}' for c in n.op)}"
    return PyCall(func=PyName(op_name), args=[left, right], kwargs=[])


def _expr_py_lambda(n: LeanLambda) -> PyExpr:
    raw_names = [p.name for p in n.params]
    clean_names = _dedup_names(raw_names)
    params = [(clean_names[i], None) for i, p in enumerate(n.params)]
    return PyLambda(args=params, body=_expr_to_py(n.body))


def _expr_py_typearrow(n: LeanTypeArrow) -> PyExpr:  # noqa: ARG001
    return PyName("Any")


def _expr_py_if(n: LeanIf) -> PyExpr:
    test = _expr_to_py(n.cond)
    then_expr = _expr_to_py(n.then_expr)
    else_expr = _expr_to_py(n.else_expr) if n.else_expr else PyConstant(None)
    return PyIfExp(test=test, body=then_expr, orelse=else_expr)


def _expr_py_match(n: LeanMatch) -> PyExpr:
    """Convert a LeanMatch used as a sub-expression into a ternary chain."""
    subject = _expr_to_py(n.expr)
    if not n.arms:
        return PyConstant(None)
    # Start with the last arm as the default value
    result: PyExpr = _expr_to_py(n.arms[-1].rhs)
    for arm in reversed(n.arms[:-1]):
        pat = arm.pattern
        body = _expr_to_py(arm.rhs)
        if isinstance(pat, LeanPatternWild):
            result = body
        elif isinstance(pat, LeanPatternNum):
            cond: PyExpr = PyCompare(
                left=subject, ops=["=="], comparators=[PyConstant(pat.value)]
            )
            result = PyIfExp(test=cond, body=body, orelse=result)
        elif isinstance(pat, LeanPatternCtor) and pat.name in ("true", "false"):
            cond = (
                subject if pat.name == "true" else PyUnaryOp(op="not", operand=subject)
            )
            result = PyIfExp(test=cond, body=body, orelse=result)
        elif isinstance(pat, LeanPatternCtor) and pat.name == "none":
            cond: PyExpr = PyCompare(
                left=subject, ops=["=="], comparators=[PyName("None")]
            )
            result = PyIfExp(test=cond, body=body, orelse=result)
        elif isinstance(pat, LeanPatternIdent):
            cond = PyCompare(
                left=subject,
                ops=["=="],
                comparators=[PyName(id=_sanitize_identifier(pat.name))],
            )
            result = PyIfExp(test=cond, body=body, orelse=result)
        else:
            continue
    return result


_EXPR_TO_PY = {
    LeanIdent: _expr_py_ident,
    LeanNum: lambda n: PyConstant(value=n.value),
    LeanFloat: lambda n: PyConstant(value=n.value),
    LeanString: lambda n: PyConstant(value=n.value),
    LeanChar: lambda n: PyConstant(value=n.value),
    LeanBool: lambda n: PyConstant(value=n.value),
    LeanUnit: lambda _: PyConstant(None),
    LeanHole: lambda _: PyName("_"),
    LeanSort: lambda _: PyName("type"),
    LeanApp: _expr_py_app,
    LeanBinOp: _expr_py_binop,
    LeanUnaryOp: lambda n: PyUnaryOp(
        op=_UNARY_OP_MAP.get(n.op, n.op), operand=_expr_to_py(n.operand)
    ),
    LeanLambda: _expr_py_lambda,
    LeanForall: lambda _: PyName("forall"),
    LeanTypeArrow: _expr_py_typearrow,
    LeanTypeSpec: lambda n: _expr_to_py(n.expr),
    LeanIf: _expr_py_if,
    LeanLet: lambda n: _expr_to_py(n.body),
    LeanProj: lambda n: PyCall(
        func=PyName(_sanitize_identifier(n.field)),
        args=[_expr_to_py(n.expr)],
        kwargs=[],
    ),
    LeanListLit: lambda n: PyList(elts=[_expr_to_py(e) for e in n.elts]),
    LeanTupleLit: lambda n: PyTuple(elts=[_expr_to_py(e) for e in n.elts]),
    LeanStructInst: lambda n: PyName(_sanitize_identifier(n.struct_name)),
    LeanMatch: _expr_py_match,
    LeanDo: lambda n: (
        _expr_to_py(n.last) if not n.stmts and n.last else PyName("do_block")
    ),
    LeanCalc: lambda _: PyName("calc_block"),
    LeanBy: lambda _: PyName("by_block"),
    LeanNamedArg: lambda n: _expr_to_py(n.value),
}


def _expr_to_py(node: LeanExpr) -> PyExpr:
    if node is None:
        return PyConstant(None)
    handler = _EXPR_TO_PY.get(type(node))
    if handler:
        return handler(node)
    return PyName("unknown")


def _pattern_to_expr(node: LeanPattern) -> PyExpr:
    if isinstance(node, LeanPatternIdent):
        name = _sanitize_identifier(node.name)
        if name == "none":
            return PyName("None")
        return PyName(id=name)
    elif isinstance(node, LeanPatternWild):
        return PyName(id="_")
    elif isinstance(node, LeanPatternNum):
        return PyConstant(value=node.value)
    elif isinstance(node, LeanPatternCtor):
        name = _sanitize_identifier(node.name)
        if name == "none":
            return PyName("None")
        if name in ("true", "false"):
            return PyConstant(value=name == "true")
        return PyName(id=name)
    elif isinstance(node, LeanPatternOr):
        if node.patterns:
            return PyMatchOr(patterns=[_pattern_to_expr(p) for p in node.patterns])
        return PyName(id="_")
    return PyName(id="_")


# ---------------------------------------------------------------------------
# _lean_type_to_py  dispatch
# ---------------------------------------------------------------------------


def _type_py_ident(n: LeanIdent) -> PyExpr:
    if n.name in _LEAN_TYPE_TO_PY:
        return _LEAN_TYPE_TO_PY[n.name]
    return PyName(id=_sanitize_identifier(n.name))


def _type_py_app(n: LeanApp) -> PyExpr:
    if isinstance(n.func, LeanIdent):
        base = n.func.name
        arg = (
            _lean_type_to_py(n.arg)
            if not isinstance(n.arg, LeanHole)
            else PyName("Any")
        )
        if base == "List":
            return PySubscript(value=PyName("list"), slice=arg)
        if base == "Option":
            return PySubscript(value=PyName("Optional"), slice=arg)
        if base == "HashMap":
            return PySubscript(value=PyName("dict"), slice=PyName("Any"))
        if base == "Set":
            return PySubscript(value=PyName("set"), slice=arg)
        if base == "Prod":
            return PyTuple(elts=[PyName("Any"), PyName("Any")])
        return PySubscript(value=PyName(_sanitize_identifier(base)), slice=arg)
    return PyName("Any")


_TYPE_TO_PY = {
    LeanIdent: _type_py_ident,
    LeanApp: _type_py_app,
    LeanTypeArrow: lambda _: PyName("Any"),
    LeanSort: lambda _: PyName("Any"),
    LeanHole: lambda _: PyName("Any"),
}


def _lean_type_to_py(node: LeanExpr) -> PyExpr:
    if node is None:
        return PyName("Any")
    handler = _TYPE_TO_PY.get(type(node))
    if handler:
        return handler(node)
    return PyName("Any")
