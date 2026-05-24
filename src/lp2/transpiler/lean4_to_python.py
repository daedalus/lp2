from typing import Optional
from lp2.ast.lean4_ast import *
from lp2.ast.python_ast import *


_LEAN_TYPE_TO_PY = {
    "Int": PyName("int"),
    "Nat": PyName("int"),
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


def lean_to_py(node: LeanNode) -> PyNode:
    if isinstance(node, LeanModule):
        body = []
        for cmd in node.body:
            py_stmt = _cmd_to_stmt(cmd)
            if py_stmt:
                body.append(py_stmt)
        return PyModule(body=body)
    raise ValueError(f"Unknown node: {type(node).__name__}")


def _cmd_to_stmt(node: LeanCommand) -> Optional[PyStmt]:
    if isinstance(node, LeanDef):
        return _def_to_func(node)
    elif isinstance(node, LeanStructure):
        return _structure_to_class(node)
    elif isinstance(node, LeanClass):
        return _structure_to_class(node)
    elif isinstance(node, LeanInductive):
        return _inductive_to_class(node)
    elif isinstance(node, LeanAxiom):
        return PyPass()
    elif isinstance(node, LeanExample):
        if node.expr:
            return PyExprStmt(expr=_expr_to_py(node.expr))
        return None
    elif isinstance(node, LeanOpen):
        return PyImport(names=node.names)
    elif isinstance(node, LeanVariable):
        return None
    elif isinstance(node, LeanNamespace):
        stmts = [_cmd_to_stmt(c) for c in node.commands]
        stmts = [s for s in stmts if s]
        return PyClassDef(name=node.name, bases=[], body=stmts)
    return None


def _def_to_func(node: LeanDef) -> PyFunctionDef:
    name = node.name
    py_args = []
    for p in node.params:
        py_ann = _lean_type_to_py(p.type) if p.type else None
        py_default = _expr_to_py(p.default) if p.default else None
        py_args.append((p.name, py_ann, py_default))

    py_return = _lean_type_to_py(node.return_type) if node.return_type else None

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
        if py_ann:
            body.append(
                PyAnnAssign(
                    target=PyName(field.name),
                    annotation=py_ann,
                    value=None,
                )
            )
        else:
            body.append(
                PyAssign(
                    target=PyName(field.name),
                    value=PyConstant(None),
                )
            )
    return PyClassDef(name=node.name, bases=[], body=body or [PyPass()])


def _inductive_to_class(node: LeanInductive) -> PyClassDef:
    ctors = []
    for ctor in node.constructors:
        field_types = []
        for f in ctor.fields:
            field_types.append(_lean_type_to_py(f.type) if f.type else PyName("Any"))
        ctors.append((ctor.name, field_types))
    body = [PyPass()]
    return PyClassDef(name=node.name, bases=[], body=body)


def _ensure_return(stmts: list[PyStmt]) -> list[PyStmt]:
    if not stmts:
        return [PyReturn(value=None)]
    if isinstance(stmts[-1], PyReturn):
        return stmts
    if isinstance(stmts[-1], PyExprStmt):
        stmts = stmts[:-1] + [PyReturn(value=stmts[-1].expr)]
        return stmts
    return stmts


def _expr_to_stmts(node: LeanExpr) -> list[PyStmt]:
    if isinstance(node, LeanLet):
        inner = _expr_to_stmts(node.body)
        val = _expr_to_py(node.value)
        assign = PyAssign(target=PyName(node.name), value=val)
        return [assign] + inner
    elif isinstance(node, LeanHave):
        inner = _expr_to_stmts(node.body)
        val = _expr_to_py(node.value)
        return [PyAssign(target=PyName(node.name or "_"), value=val)] + inner
    elif isinstance(node, LeanIf):
        test = _expr_to_py(node.cond)
        then_stmts = _expr_to_stmts(node.then_expr)
        else_stmts = _expr_to_stmts(node.else_expr) if node.else_expr else []
        return [PyIf(test=test, body=then_stmts, orelse=else_stmts)]
    elif isinstance(node, LeanMatch):
        subject = _expr_to_py(node.expr)
        cases = []
        for arm in node.arms:
            pat = _pattern_to_expr(arm.pattern)
            body = _expr_to_stmts(arm.rhs)
            guard = PyName("True")  # simplified
            cases.append(PyMatchCase(pattern=pat, guard=None, body=body))
        return [PyMatch(subject=subject, cases=cases)]
    elif (
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
    elif isinstance(node, LeanLambda) and len(node.params) == 1:
        return [PyReturn(value=_expr_to_py(node))]
    elif isinstance(node, LeanUnit):
        return [PyReturn(value=None)]
    else:
        py_expr = _expr_to_py(node)
        if isinstance(py_expr, PyName) and py_expr.id == "true":
            return [PyReturn(value=PyConstant(True))]
        elif isinstance(py_expr, PyName) and py_expr.id == "false":
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


def _expr_to_py(node: LeanExpr) -> PyExpr:
    if node is None:
        return PyConstant(None)
    if isinstance(node, LeanIdent):
        name = node.name
        if name == "none":
            return PyConstant(None)
        if name == "true":
            return PyConstant(True)
        if name == "false":
            return PyConstant(False)
        return PyName(id=name)
    elif isinstance(node, LeanNum):
        if node.is_nat:
            return PyConstant(value=node.value)
        return PyConstant(value=node.value)
    elif isinstance(node, LeanFloat):
        return PyConstant(value=node.value)
    elif isinstance(node, LeanString):
        return PyConstant(value=node.value)
    elif isinstance(node, LeanChar):
        return PyConstant(value=node.value)
    elif isinstance(node, LeanBool):
        return PyConstant(value=node.value)
    elif isinstance(node, LeanUnit):
        return PyConstant(None)
    elif isinstance(node, LeanHole):
        return PyName("_")
    elif isinstance(node, LeanSort):
        return PyName("type")
    elif isinstance(node, LeanApp):
        if isinstance(node.func, LeanIdent) and node.func.name == "List.cons":
            if isinstance(node.arg, LeanListLit):
                return PyList(elts=[_expr_to_py(e) for e in node.arg.elts])
            if isinstance(node.arg, LeanIdent) and node.arg.name == "List.nil":
                return PyList(elts=[_expr_to_py(node.func)])
            return PyList(elts=[_expr_to_py(node.func), _expr_to_py(node.arg)])
        elif (
            isinstance(node.func, LeanApp)
            and isinstance(node.func.func, LeanIdent)
            and node.func.func.name == "Prod.mk"
        ):
            left = _expr_to_py(node.func.arg)
            right = _expr_to_py(node.arg)
            if isinstance(left, PyTuple) and isinstance(right, PyExpr):
                return PyTuple(elts=left.elts + [right])
            return PyTuple(elts=[left, right])
        args, func = _collect_app_args(node)
        func_expr = _expr_to_py(func)
        py_args = [_expr_to_py(a) for a in args]
        return PyCall(func=func_expr, args=py_args, kwargs=[])
    elif isinstance(node, LeanBinOp):
        op_map = {
            "+": "+",
            "-": "-",
            "*": "*",
            "/": "/",
            "%": "%",
            "=": "==",
            "==": "==",
            "!=": "!=",
            "≠": "!=",
            "!=": "!=",
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
            "::": "::",
            "|>": "|>",
            "^": "^",
            "++": "+",
        }
        left = _expr_to_py(node.left)
        right = _expr_to_py(node.right)
        py_op = op_map.get(node.op, node.op)
        if py_op == "::":
            if isinstance(right, PyList):
                return PyList(elts=[left] + right.elts)
            return PyList(elts=[left, right])
        if (
            isinstance(left, PyConstant)
            and isinstance(right, PyConstant)
            and isinstance(left.value, str)
            and isinstance(right.value, str)
        ):
            pass
        return PyBinOp(left=left, op=py_op, right=right)
    elif isinstance(node, LeanUnaryOp):
        operand = _expr_to_py(node.operand)
        return PyUnaryOp(op=node.op, operand=operand)
    elif isinstance(node, LeanLambda):
        params = []
        for p in node.params:
            params.append((p.name, _lean_type_to_py(p.type) if p.type else None))
        body = _expr_to_py(node.body)
        return PyLambda(args=params, body=body)
    elif isinstance(node, LeanForall):
        return PyName("forall")
    elif isinstance(node, LeanTypeArrow):
        left = _expr_to_py(node.from_type)
        right = _expr_to_py(node.to_type)
        return PyBinOp(left=left, op="->", right=right)
    elif isinstance(node, LeanTypeSpec):
        expr = _expr_to_py(node.expr)
        return expr
    elif isinstance(node, LeanIf):
        test = _expr_to_py(node.cond)
        then_expr = _expr_to_py(node.then_expr)
        else_expr = _expr_to_py(node.else_expr) if node.else_expr else PyConstant(None)
        return PyIfExp(test=test, body=then_expr, orelse=else_expr)
    elif isinstance(node, LeanLet):
        body = _expr_to_py(node.body)
        return body
    elif isinstance(node, LeanProj):
        return PyAttribute(value=_expr_to_py(node.expr), attr=node.field)
    elif isinstance(node, LeanListLit):
        return PyList(elts=[_expr_to_py(e) for e in node.elts])
    elif isinstance(node, LeanTupleLit):
        return PyTuple(elts=[_expr_to_py(e) for e in node.elts])
    elif isinstance(node, LeanStructInst):
        return PyName(node.struct_name)
    elif isinstance(node, LeanMatch):
        subject = _expr_to_py(node.expr)
        return PyCall(func=PyName("match"), args=[subject], kwargs=[])
    elif isinstance(node, LeanDo):
        return PyName("do_block")
    elif isinstance(node, LeanCalc):
        return PyName("calc_block")
    elif isinstance(node, LeanBy):
        return PyName("by_block")
    elif isinstance(node, LeanNamedArg):
        return _expr_to_py(node.value)
    return PyName("unknown")


def _pattern_to_expr(node: LeanPattern) -> PyExpr:
    if isinstance(node, LeanPatternIdent):
        return PyName(id=node.name)
    elif isinstance(node, LeanPatternWild):
        return PyName(id="_")
    elif isinstance(node, LeanPatternNum):
        return PyConstant(value=node.value)
    elif isinstance(node, LeanPatternCtor):
        if node.name in ("true", "false"):
            return PyConstant(value=node.name == "true")
        return PyName(id=node.name)
    elif isinstance(node, LeanPatternOr):
        if node.patterns:
            return _pattern_to_expr(node.patterns[0])
        return PyName(id="_")
    return PyName(id="_")


def _lean_type_to_py(node: LeanExpr) -> PyExpr:
    if node is None:
        return PyName("Any")
    if isinstance(node, LeanIdent):
        name = node.name
        if name in _LEAN_TYPE_TO_PY:
            return _LEAN_TYPE_TO_PY[name]
        return PyName(id=name)
    elif isinstance(node, LeanApp):
        if isinstance(node.func, LeanIdent):
            base = node.func.name
            arg = (
                _lean_type_to_py(node.arg)
                if not isinstance(node.arg, LeanHole)
                else PyName("Any")
            )
            if base == "List":
                return PySubscript(value=PyName("list"), slice=arg)
            elif base == "Option":
                return PySubscript(value=PyName("Optional"), slice=arg)
            elif base == "HashMap":
                return PySubscript(value=PyName("dict"), slice=PyName("Any"))
            elif base == "Set":
                return PySubscript(value=PyName("set"), slice=arg)
            elif base == "Prod":
                return PyTuple(elts=[PyName("Any"), PyName("Any")])
            return PySubscript(value=PyName(base), slice=arg)
        return PyName("Any")
    elif isinstance(node, LeanTypeArrow):
        from_type = (
            _lean_type_to_py(node.from_type) if node.from_type else PyName("Any")
        )
        to_type = _lean_type_to_py(node.to_type) if node.to_type else PyName("Any")
        return PyName("Any")
    elif isinstance(node, LeanSort):
        return PyName("Any")
    elif isinstance(node, LeanHole):
        return PyName("Any")
    return PyName("Any")
