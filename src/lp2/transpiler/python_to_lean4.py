import importlib
import inspect

from lp2.ast.lean4_ast import *
from lp2.ast.python_ast import *
from lp2.parser.python_parser import parse_python

# Config: when True, map Python `int` to `Nat` instead of `Int`.
# Nat works with omega and supports structural recursion.
USE_NAT: bool = True

_PY_TYPE_TO_LEAN = {
    "int": LeanIdent("Nat") if USE_NAT else LeanIdent("Int"),
    "float": LeanIdent("Float"),
    "bool": LeanIdent("Bool"),
    "str": LeanIdent("String"),
    "bytes": LeanIdent("ByteArray"),
    "None": LeanIdent("Unit"),
    "list": LeanIdent("List"),
    "tuple": LeanIdent("Prod"),
    "dict": LeanIdent("HashMap"),
    "set": LeanIdent("Set"),
}


_LEAN_TYPE_KW = {
    "Nat": "Nat",
    "Int": "Int",
    "Float": "Float",
    "Bool": "Bool",
    "String": "String",
    "Char": "Char",
    "Unit": "Unit",
    "List": "List",
    "Option": "Option",
    "Prod": "Prod",
}


_NAME_ESCAPE = {
    "def": "def_",
    "match": "match_",
    "if": "if_",
    "else": "else_",
    "then": "then_",
    "let": "let_",
    "in": "in_",
    "do": "do_",
    "for": "for_",
    "while": "while_",
    "class": "class_",
    "try": "try_",
    "except": "except_",
    "raise": "raise_",
    "with": "with_",
    "return": "return_",
    "and": "and_",
    "or": "or_",
    "not": "not_",
    "true": "true_",
    "false": "false_",
    "instance": "instance_",
    "open": "open_",
}


def _escape_name(name: str) -> str:
    return _NAME_ESCAPE.get(name, name)


def _make_get_helper() -> LeanDef:
    get_body = LeanMatch(
        expr=LeanIdent("xs"),
        arms=[
            LeanMatchArm(
                pattern=LeanPatternCtor(
                    name="List.cons",
                    patterns=[
                        LeanPatternIdent(name="h"),
                        LeanPatternIdent(name="t"),
                    ],
                ),
                rhs=LeanIf(
                    cond=LeanBinOp(left=LeanIdent("i"), op="=", right=LeanNum(0)),
                    then_expr=LeanIdent("h"),
                    else_expr=LeanApp(
                        func=LeanApp(func=LeanIdent("get"), arg=LeanIdent("t")),
                        arg=LeanBinOp(left=LeanIdent("i"), op="-", right=LeanNum(1)),
                    ),
                ),
            ),
            LeanMatchArm(
                pattern=LeanPatternCtor(name="List.nil", patterns=[]),
                rhs=LeanNum(0),
            ),
        ],
    )
    elem_type = LeanIdent("Nat") if USE_NAT else LeanIdent("Int")
    return LeanDef(
        name="get",
        is_partial=True,
        params=[
            LeanParam(
                name="xs",
                type=LeanApp(func=LeanIdent("List"), arg=elem_type),
            ),
            LeanParam(name="i", type=LeanIdent("Nat")),
        ],
        return_type=elem_type,
        value=get_body,
    )


def _make_list_add_instance() -> LeanInstance:
    elem_type = LeanIdent("Nat") if USE_NAT else LeanIdent("Int")
    return LeanInstance(
        name="",
        params=[],
        type=LeanApp(
            func=LeanIdent("Add"),
            arg=LeanApp(func=LeanIdent("List"), arg=elem_type),
        ),
        methods=[
            LeanDef(
                name="add",
                params=[],
                return_type=None,
                value=LeanIdent("List.append"),
            )
        ],
        is_local=True,
    )


def _make_popcount_shim() -> LeanDef:
    return LeanDef(
        name="Nat.popCount",
        params=[LeanParam(name="n", type=LeanIdent("Nat"))],
        return_type=LeanIdent("Nat"),
        value=LeanMatch(
            expr=LeanIdent("n"),
            arms=[
                LeanMatchArm(
                    pattern=LeanPatternCtor(name="Nat.zero", patterns=[]),
                    rhs=LeanNum(0),
                ),
                LeanMatchArm(
                    pattern=LeanPatternCtor(
                        name="Nat.succ",
                        patterns=[LeanPatternIdent(name="n")],
                    ),
                    rhs=LeanBinOp(
                        left=LeanBinOp(
                            left=LeanApp(
                                func=LeanIdent("Nat.succ"),
                                arg=LeanIdent("n"),
                            ),
                            op="&&&",
                            right=LeanNum(1),
                        ),
                        op="+",
                        right=LeanApp(
                            func=LeanIdent("Nat.popCount"),
                            arg=LeanBinOp(
                                left=LeanApp(
                                    func=LeanIdent("Nat.succ"),
                                    arg=LeanIdent("n"),
                                ),
                                op=">>>",
                                right=LeanNum(1),
                            ),
                        ),
                    ),
                ),
            ],
        ),
    )


def _make_set_helper() -> LeanDef:
    set_body = LeanMatch(
        expr=LeanIdent("xs"),
        arms=[
            LeanMatchArm(
                pattern=LeanPatternCtor(
                    name="List.cons",
                    patterns=[
                        LeanPatternIdent(name="h"),
                        LeanPatternIdent(name="t"),
                    ],
                ),
                rhs=LeanIf(
                    cond=LeanBinOp(left=LeanIdent("i"), op="=", right=LeanNum(0)),
                    then_expr=LeanApp(
                        func=LeanApp(func=LeanIdent("List.cons"), arg=LeanIdent("x")),
                        arg=LeanIdent("t"),
                    ),
                    else_expr=LeanApp(
                        func=LeanApp(
                            func=LeanApp(func=LeanIdent("set"), arg=LeanIdent("t")),
                            arg=LeanBinOp(
                                left=LeanIdent("i"), op="-", right=LeanNum(1)
                            ),
                        ),
                        arg=LeanIdent("x"),
                    ),
                ),
            ),
            LeanMatchArm(
                pattern=LeanPatternCtor(name="List.nil", patterns=[]),
                rhs=LeanIdent("List.nil"),
            ),
        ],
    )
    elem_type = LeanIdent("Nat") if USE_NAT else LeanIdent("Int")
    return LeanDef(
        name="set",
        is_partial=True,
        params=[
            LeanParam(
                name="xs",
                type=LeanApp(func=LeanIdent("List"), arg=elem_type),
            ),
            LeanParam(name="i", type=LeanIdent("Nat")),
            LeanParam(name="x", type=elem_type),
        ],
        return_type=LeanApp(func=LeanIdent("List"), arg=elem_type),
        value=set_body,
    )


_uses_list: bool = False
_uses_set: bool = False
_uses_popcount: bool = False
_imported_modules: dict[str, object] = {}
_generated_helpers: list[LeanCommand] = []
_transpiling_helper: bool = False


def _expr_list(node: PyList) -> LeanExpr:
    global _uses_list
    _uses_list = True
    elts = [_expr_to_lean(e) for e in node.elts]
    if not elts:
        return LeanIdent("List.nil")
    result: LeanExpr = LeanIdent("List.nil")
    for e in reversed(elts):
        result = LeanApp(func=LeanApp(func=LeanIdent("List.cons"), arg=e), arg=result)
    return result


def py_to_lean(node: PyNode) -> LeanNode:
    global _uses_subscript, _uses_list, _uses_set, _uses_popcount, _imported_modules, _generated_helpers, _transpiling_helper
    _uses_subscript = False
    _uses_list = False
    _uses_set = False
    _uses_popcount = False
    _imported_modules = {}
    _generated_helpers = []
    _transpiling_helper = False
    if isinstance(node, PyModule):
        body = []
        for stmt in node.body:
            lean_cmd = _stmt_to_lean_cmd(stmt)
            if lean_cmd:
                body.append(lean_cmd)
        if _uses_popcount:
            body.insert(0, _make_popcount_shim())
        if _uses_subscript:
            body.insert(0, _make_get_helper())
        if _uses_set:
            body.insert(0, _make_set_helper())
        if _uses_list:
            body.insert(0, _make_list_add_instance())
        if _generated_helpers:
            for cmd in reversed(_generated_helpers):
                body.insert(0, cmd)
        return LeanModule(imports=[], body=body)
    raise ValueError(f"Unknown node: {type(node).__name__}")


# ── Helper functions (shared across dispatch handlers) ───────────────


def _has_rec_let(expr: LeanExpr) -> bool:
    if isinstance(expr, LeanLet) and expr.is_rec:
        return True
    for attr, val in vars(expr).items():
        if isinstance(val, LeanExpr):
            if _has_rec_let(val):
                return True
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, LeanExpr) and _has_rec_let(item):
                    return True
    return False


def _is_recursive(name: str, expr: LeanExpr) -> bool:
    if isinstance(expr, LeanIdent) and expr.name == name:
        return True
    if isinstance(expr, LeanApp):
        return _is_recursive(name, expr.func) or _is_recursive(name, expr.arg)
    if isinstance(expr, LeanBinOp):
        return _is_recursive(name, expr.left) or _is_recursive(name, expr.right)
    if isinstance(expr, LeanUnaryOp):
        return _is_recursive(name, expr.operand)
    if isinstance(expr, LeanIf):
        return (
            _is_recursive(name, expr.cond)
            or _is_recursive(name, expr.then_expr)
            or (expr.else_expr is not None and _is_recursive(name, expr.else_expr))
        )
    if isinstance(expr, LeanLet):
        if expr.value and _is_recursive(name, expr.value):
            return True
        return _is_recursive(name, expr.body)
    if isinstance(expr, LeanMatch):
        return _is_recursive(name, expr.expr) or any(
            _is_recursive(name, a.rhs) for a in expr.arms
        )
    if isinstance(expr, LeanLambda):
        return _is_recursive(name, expr.body)
    if isinstance(expr, LeanProj):
        return _is_recursive(name, expr.expr)
    from lp2.ast.lean4_ast import LeanTypeSpec

    if isinstance(expr, LeanTypeSpec):
        return _is_recursive(name, expr.expr) or _is_recursive(name, expr.type)
    return False


def _contains_yield(stmts: list[PyStmt]) -> bool:
    for stmt in stmts:
        if isinstance(stmt, PyExprStmt) and isinstance(stmt.expr, PyYield):
            return True
        if isinstance(stmt, PyIf):
            if _contains_yield(stmt.body) or _contains_yield(stmt.orelse):
                return True
        if isinstance(stmt, PyWhile) and _contains_yield(stmt.body):
            return True
        if isinstance(stmt, PyFor) and _contains_yield(stmt.body):
            return True
    return False


def _transform_generator_body(body: list[PyStmt]) -> list[PyStmt]:
    result_var = PyName(id="__yield_result__")

    def _walk(stmts: list[PyStmt]) -> list[PyStmt]:
        transformed: list[PyStmt] = []
        for stmt in stmts:
            if isinstance(stmt, PyExprStmt) and isinstance(stmt.expr, PyYield):
                yield_val = stmt.expr.value
                if yield_val is not None:
                    transformed.append(
                        PyAugAssign(
                            target=PyName(id="__yield_result__"),
                            op="+=",
                            value=PyList(elts=[yield_val]),
                        )
                    )
            elif isinstance(stmt, PyIf):
                transformed.append(
                    PyIf(
                        test=stmt.test,
                        body=_walk(stmt.body),
                        orelse=_walk(stmt.orelse) if stmt.orelse else [],
                    )
                )
            elif isinstance(stmt, PyWhile):
                transformed.append(PyWhile(test=stmt.test, body=_walk(stmt.body)))
            elif isinstance(stmt, PyFor):
                transformed.append(
                    PyFor(target=stmt.target, iter=stmt.iter, body=_walk(stmt.body))
                )
            elif isinstance(stmt, PyReturn):
                transformed.append(PyReturn(value=result_var))
            else:
                transformed.append(stmt)
        return transformed

    new_body = _walk(body)
    new_body.insert(0, PyAssign(target=result_var, value=PyList(elts=[])))

    has_return = any(isinstance(s, PyReturn) for s in new_body)
    if not has_return:
        new_body.append(PyReturn(value=result_var))

    return new_body


def _func_to_lean(node: PyFunctionDef) -> LeanDef:
    name = _escape_name(node.name)
    params = []
    for arg_name, annotation, default in node.args:
        lean_ann = None
        if annotation:
            lean_ann = _py_type_to_lean_type(annotation)
        kwargs = {}
        if default is not None:
            kwargs["default"] = _expr_to_lean(default)
        params.append(LeanParam(name=_escape_name(arg_name), type=lean_ann, **kwargs))

    is_generator = _contains_yield(node.body)

    return_type = None
    if node.return_type:
        return_type = _py_type_to_lean_type(node.return_type)
    elif is_generator:
        return_type = LeanApp(func=LeanIdent("List"), arg=LeanHole())
    else:
        return_type = LeanIdent("Unit")

    body_stmts = [s for s in (_transform_generator_body(node.body) if is_generator else node.body) if not isinstance(s, PySkipTranspile)]

    if len(body_stmts) == 1 and isinstance(body_stmts[0], PyReturn):
        body = (
            _expr_to_lean(body_stmts[0].value)
            if body_stmts[0].value
            else LeanIdent("Unit")
        )
    else:
        body = _stmts_to_lean_expr(body_stmts)

    is_partial = _has_rec_let(body) if body else False
    is_recursive = False
    if not is_partial and body is not None:
        is_partial = _is_recursive(name, body)
        is_recursive = is_partial

    # Heuristic: if recursive on a single Nat param (and USE_NAT), add termination_by
    tb = None
    dec = None
    if USE_NAT and is_recursive and body is not None:
        nat_params = [p for p in params if isinstance(p.type, LeanIdent) and p.type.name == "Nat"]
        if len(nat_params) == 1:
            tb = LeanIdent(nat_params[0].name)
            dec = "omega"
            # termination_by replaces partial
            is_partial = False

    return LeanDef(
        name=name,
        params=params,
        return_type=return_type,
        value=body,
        is_partial=is_partial,
        termination_by=tb,
        decreasing_by=dec,
    )


def _class_to_lean(node: PyClassDef) -> LeanStructure:
    name = _escape_name(node.name)
    fields = []
    for stmt in node.body:
        if isinstance(stmt, PyAnnAssign) or isinstance(stmt, PyAssign):
            field_name = _get_field_name(stmt.target)
            if field_name:
                ann = stmt.annotation if isinstance(stmt, PyAnnAssign) else None
                lean_ann = _py_type_to_lean_type(ann) if ann else None
                fields.append(
                    LeanParam(
                        name=_escape_name(field_name), type=lean_ann or LeanHole()
                    )
                )
    return LeanStructure(name=name, params=[], extends=[], fields=fields)


def _get_field_name(node: PyExpr) -> str | None:
    if isinstance(node, PyName):
        return node.id
    return None


def _assign_to_lean(node) -> LeanCommand | None:
    return None


def _assign_target_name(node: PyExpr) -> str:
    if isinstance(node, PyName):
        return node.id
    if isinstance(node, PySubscript) and isinstance(node.value, PyName):
        return node.value.id
    return "_"


def _make_subscript_assign(target: PySubscript, value: LeanExpr) -> LeanExpr:
    global _uses_set
    _uses_set = True
    return LeanApp(
        func=LeanApp(
            func=LeanApp(func=LeanIdent("set"), arg=_expr_to_lean(target.value)),
            arg=_expr_to_lean(target.slice),
        ),
        arg=value,
    )


_AUG_OPS = {
    "+": "+",
    "-": "-",
    "*": "*",
    "/": "/",
    "%": "%",
    "^": "^",
    "&&&": "&&&",
    "|||": "|||",
    "^^^": "^^^",
    "<<<": "<<<",
    ">>>": ">>>",
}


def _strip_aug_op(op: str) -> str:
    return _AUG_OPS.get(op, op.rstrip("="))


def _to_bool(expr: LeanExpr, py_cond: PyExpr | None = None) -> LeanExpr:
    """Wrap *expr* so it's a ``Bool`` suitable for ``if``/``while``.

    Python truthiness for numbers means ``!= 0``.  If the original
    Python condition is already a comparison or a ``bool`` literal we
    leave it alone.
    """
    # If we have the original Python node, skip wrapping for:
    #   - comparisons (a > b, x == y …)
    #   - boolean ops (a and b, not c …)
    #   - bool constants (True / False)
    if py_cond is not None and isinstance(
        py_cond,
        (PyCompare, PyBoolOp, PyUnaryOp),
    ):
        return expr
    if isinstance(py_cond, PyConstant) and isinstance(py_cond.value, bool):
        return expr

    return LeanBinOp(left=expr, op="≠", right=LeanNum(0))


def _call_to_lean_print(node: PyCall) -> LeanExpr:
    if node.args:
        return LeanApp(func=LeanIdent("IO.println"), arg=_expr_to_lean(node.args[0]))
    return LeanIdent("IO.println")


def _py_pat_to_lean(node: PyExpr) -> LeanPattern:
    if isinstance(node, PyName):
        if node.id == "_":
            return LeanPatternWild()
        return LeanPatternIdent(name=_escape_name(node.id))
    elif isinstance(node, PyConstant):
        if isinstance(node.value, int):
            return LeanPatternNum(value=node.value)
        elif isinstance(node.value, bool):
            return LeanPatternCtor(name="true" if node.value else "false", patterns=[])
        elif node.value is None:
            return LeanPatternCtor(name="none", patterns=[])
        return LeanPatternIdent(name=repr(node.value))
    elif isinstance(node, PyMatchOr):
        return LeanPatternOr(patterns=[_py_pat_to_lean(p) for p in node.patterns])
    return LeanPatternWild()


# ── Dispatch handlers for _stmt_to_lean_cmd ──────────────────────────


def _cmd_func_def(node: PyFunctionDef) -> LeanCommand | None:
    return _func_to_lean(node)


def _cmd_class_def(node: PyClassDef) -> LeanCommand | None:
    return _class_to_lean(node)


def _cmd_assign(node) -> LeanCommand | None:
    return _assign_to_lean(node)


def _cmd_aug_assign(node) -> LeanCommand | None:
    return None


def _cmd_import(node: PyImport) -> LeanCommand | None:
    for name in node.names:
        mod_name = name.split(".")[0]
        if mod_name not in _imported_modules:
            try:
                _imported_modules[mod_name] = importlib.import_module(mod_name)
            except ImportError:
                pass
    return None


def _cmd_expr_stmt(node: PyExprStmt) -> LeanCommand | None:
    if (
        isinstance(node.expr, PyCall)
        and isinstance(node.expr.func, PyName)
        and node.expr.func.id in ("print", "eval")
    ):
        if node.expr.func.id == "print":
            return LeanExample(expr=_call_to_lean_print(node.expr))
        return LeanExample(
            expr=_expr_to_lean(node.expr.args[0]) if node.expr.args else LeanUnit()
        )
    return LeanExample(expr=_expr_to_lean(node.expr))


def _cmd_skip_transpile(node: PySkipTranspile) -> LeanCommand | None:
    prefix = f"-- no_transpile ({node.reason})"
    lines = [f"--   {line}" for line in node.source_lines]
    return LeanRaw(text=prefix + "\n" + "\n".join(lines))


_STMT_TO_CMD = {
    PyFunctionDef: _cmd_func_def,
    PyClassDef: _cmd_class_def,
    PyAssign: _cmd_assign,
    PyAnnAssign: _cmd_assign,
    PyAugAssign: _cmd_aug_assign,
    PyImport: _cmd_import,
    PyExprStmt: _cmd_expr_stmt,
    PySkipTranspile: _cmd_skip_transpile,
}


def _stmt_to_lean_cmd(node: PyStmt) -> LeanCommand | None:
    handler = _STMT_TO_CMD.get(type(node))
    if handler:
        return handler(node)
    return None


# ── Dispatch handlers for _stmts_to_lean_expr (fold helpers) ────────


def _fold_assign_like(s, result: LeanExpr) -> LeanExpr:
    target = _assign_target_name(s.target)
    if isinstance(s.target, PySubscript):
        value = _make_subscript_assign(s.target, _expr_to_lean(s.value))
    else:
        value = _expr_to_lean(s.value)
    return LeanLet(
        name=_escape_name(target),
        params=[],
        type=None,
        value=value,
        body=result,
    )


def _fold_aug_assign(s: PyAugAssign, result: LeanExpr) -> LeanExpr:
    target = _assign_target_name(s.target)
    op = _strip_aug_op(s.op)
    value = _expr_to_lean(s.value)
    if isinstance(s.target, PySubscript):
        target_expr = _expr_to_lean(s.target)
        binop = LeanBinOp(left=target_expr, op=op, right=value)
        value = _make_subscript_assign(s.target, binop)
    else:
        target_expr = _expr_to_lean(s.target)
        value = LeanBinOp(left=target_expr, op=op, right=value)
    return LeanLet(
        name=_escape_name(target),
        params=[],
        type=None,
        value=value,
        body=result,
    )


def _append_continuation(expr: LeanExpr, cont: LeanExpr) -> LeanExpr:
    if isinstance(expr, LeanUnit):
        return cont
    elif isinstance(expr, LeanLet):
        return LeanLet(
            name=expr.name,
            params=expr.params,
            type=expr.type,
            value=expr.value,
            body=_append_continuation(expr.body, cont),
            is_mut=expr.is_mut,
            is_rec=expr.is_rec,
        )
    elif isinstance(expr, LeanIf):
        return LeanIf(
            cond=expr.cond,
            then_expr=_append_continuation(expr.then_expr, cont),
            else_expr=_append_continuation(expr.else_expr, cont)
            if expr.else_expr
            else None,
        )
    elif isinstance(expr, LeanApp):
        return LeanApp(
            func=_append_continuation(expr.func, cont),
            arg=_append_continuation(expr.arg, cont),
        )
    return expr


def _fold_if(s: PyIf, result: LeanExpr) -> LeanExpr:
    test = _to_bool(_expr_to_lean(s.test), s.test)
    then_body = _stmts_to_lean_expr(s.body) if s.body else LeanUnit()
    if not s.orelse:
        then_body = _append_continuation(then_body, result)
        if isinstance(result, LeanLet) and result.is_rec:
            if_stmt = LeanIf(cond=test, then_expr=then_body, else_expr=result.body)
            return LeanLet(
                name=result.name,
                params=result.params,
                type=result.type,
                value=result.value,
                body=if_stmt,
                is_rec=True,
            )
        return LeanIf(cond=test, then_expr=then_body, else_expr=result)
    else_body = _stmts_to_lean_expr(s.orelse)
    then_body = _append_continuation(then_body, result)
    else_body = _append_continuation(else_body, result)
    return LeanIf(cond=test, then_expr=then_body, else_expr=else_body)


def _fold_while(s: PyWhile, result: LeanExpr) -> LeanExpr:
    carried = _find_carried_vars(s.body, s.test)
    body = _stmts_to_lean_expr(s.body)
    body = _replace_carried_assign(body, carried, "while_loop")
    test = _to_bool(_expr_to_lean(s.test), s.test)
    body = LeanIf(cond=test, then_expr=body, else_expr=result)

    hole_type = LeanIdent("Nat") if USE_NAT else LeanHole()
    loop_params = [LeanParam(name=v, type=hole_type) for v in sorted(carried)]
    init_args = [LeanIdent(v) for v in sorted(carried)]

    loop_call: LeanExpr = (
        LeanApp(func=LeanIdent("while_loop"), arg=init_args[0])
        if len(init_args) == 1
        else LeanUnit()
    )
    if len(init_args) > 1:
        loop_call = LeanApp(func=LeanIdent("while_loop"), arg=init_args[0])
        for a in init_args[1:]:
            loop_call = LeanApp(func=loop_call, arg=a)

    if not carried:
        return body

    return LeanLet(
        name="while_loop",
        params=loop_params,
        type=hole_type,
        value=body,
        body=loop_call,
        is_rec=True,
    )


def _prepend_arg_to_loop(expr: LeanExpr, arg_expr: LeanExpr) -> LeanExpr:
    if (
        isinstance(expr, LeanApp)
        and isinstance(expr.func, LeanIdent)
        and expr.func.name == "loop"
    ):
        return LeanApp(func=LeanApp(func=LeanIdent("loop"), arg=arg_expr), arg=expr.arg)
    elif isinstance(expr, LeanApp):
        return LeanApp(func=_prepend_arg_to_loop(expr.func, arg_expr), arg=expr.arg)
    elif isinstance(expr, LeanIf):
        return LeanIf(
            cond=expr.cond,
            then_expr=_prepend_arg_to_loop(expr.then_expr, arg_expr),
            else_expr=_prepend_arg_to_loop(expr.else_expr, arg_expr)
            if expr.else_expr
            else None,
        )
    elif isinstance(expr, LeanLet):
        return LeanLet(
            name=expr.name,
            params=expr.params,
            type=expr.type,
            value=_prepend_arg_to_loop(expr.value, arg_expr) if expr.value else None,
            body=_prepend_arg_to_loop(expr.body, arg_expr),
            is_mut=expr.is_mut,
            is_rec=expr.is_rec,
        )
    return expr


def _make_for_range_loop(
    target_name: str,
    range_args: list[PyExpr],
    body_stmts: list[PyStmt],
    carried: set[str],
    result: LeanExpr,
) -> LeanExpr:
    if len(range_args) == 1:
        start = PyConstant(0)
        end = range_args[0]
        step = PyConstant(1)
    elif len(range_args) == 2:
        start = range_args[0]
        end = range_args[1]
        step = PyConstant(1)
    else:
        start = range_args[0]
        end = range_args[1]
        step_val = range_args[2]
        step_expr = _expr_to_lean(step_val)
        start_expr = _expr_to_lean(start)
        end_expr = _expr_to_lean(end)
        body = _stmts_to_lean_expr(body_stmts)
        body = _replace_carried_assign(body, carried, "loop")
        inc_expr = LeanBinOp(left=LeanIdent(target_name), op="+", right=step_expr)
        if carried:
            body = _prepend_arg_to_loop(body, inc_expr)
        else:
            loop_call = LeanApp(func=LeanIdent("loop"), arg=inc_expr)
            if isinstance(body, LeanUnit):
                body = loop_call
            elif isinstance(body, LeanLet):
                body = _append_continuation(body, loop_call)
            else:
                body = LeanLet(
                    name="_", params=[], type=None, value=body, body=loop_call
                )
        cond = LeanBinOp(left=LeanIdent(target_name), op="<", right=end_expr)
        body = LeanIf(cond=cond, then_expr=body, else_expr=result)
        all_carried = [target_name] + sorted(carried)
        hole_type = LeanIdent("Nat") if USE_NAT else LeanHole()
        loop_params = [LeanParam(name=v, type=hole_type) for v in all_carried]
        init_args: list[LeanExpr] = [start_expr] + [
            LeanIdent(v) for v in sorted(carried)
        ]
        loop_call_init: LeanExpr = LeanIdent("loop")
        for a in init_args:
            loop_call_init = LeanApp(func=loop_call_init, arg=a)
        return LeanLet(
            name="loop",
            params=loop_params,
            type=hole_type,
            value=body,
            body=loop_call_init,
            is_rec=True,
        )

    end_expr = _expr_to_lean(end)
    step_expr = _expr_to_lean(step)

    body = _stmts_to_lean_expr(body_stmts)
    body = _replace_carried_assign(body, carried, "loop")

    inc_expr = LeanBinOp(left=LeanIdent(target_name), op="+", right=step_expr)

    if carried:
        body = _prepend_arg_to_loop(body, inc_expr)
    else:
        loop_call = LeanApp(func=LeanIdent("loop"), arg=inc_expr)
        if isinstance(body, LeanUnit):
            body = loop_call
        elif isinstance(body, LeanLet):
            body = _append_continuation(body, loop_call)
        else:
            body = LeanLet(name="_", params=[], type=None, value=body, body=loop_call)

    cond = LeanBinOp(left=LeanIdent(target_name), op="<", right=end_expr)
    body = LeanIf(cond=cond, then_expr=body, else_expr=result)

    all_carried = [target_name] + sorted(carried)
    hole_type = LeanIdent("Nat") if USE_NAT else LeanHole()
    loop_params = [LeanParam(name=v, type=hole_type) for v in all_carried]
    start_expr = _expr_to_lean(start)
    init_args = [start_expr] + [LeanIdent(v) for v in sorted(carried)]
    loop_call_init: LeanExpr = LeanIdent("loop")
    for a in init_args:
        loop_call_init = LeanApp(func=loop_call_init, arg=a)

    return LeanLet(
        name="loop",
        params=loop_params,
        type=hole_type,
        value=body,
        body=loop_call_init,
        is_rec=True,
    )


def _make_for_list_loop(
    target_name: str,
    iter_expr: LeanExpr,
    body_stmts: list[PyStmt],
    carried: set[str],
    result: LeanExpr,
) -> LeanExpr:
    tail_name = "__xs_tail"

    body = _stmts_to_lean_expr(body_stmts)
    body = _replace_carried_assign(body, carried, "loop")

    if carried:
        body = _prepend_arg_to_loop(body, LeanIdent(tail_name))
    else:
        loop_call = LeanApp(func=LeanIdent("loop"), arg=LeanIdent(tail_name))
        if isinstance(body, LeanUnit):
            body = loop_call
        elif isinstance(body, LeanLet):
            body = _append_continuation(body, loop_call)
        else:
            body = LeanLet(name="_", params=[], type=None, value=body, body=loop_call)

    match = LeanMatch(
        expr=LeanIdent(tail_name),
        arms=[
            LeanMatchArm(
                pattern=LeanPatternCtor(name="List.nil", patterns=[]),
                rhs=result,
            ),
            LeanMatchArm(
                pattern=LeanPatternCtor(
                    name="List.cons",
                    patterns=[
                        LeanPatternIdent(name=target_name),
                        LeanPatternIdent(name=tail_name),
                    ],
                ),
                rhs=body,
            ),
        ],
    )

    hole_type = LeanIdent("Nat") if USE_NAT else LeanHole()
    list_type = LeanApp(func=LeanIdent("List"), arg=hole_type)
    loop_params = [LeanParam(name=tail_name, type=list_type)]
    for v in sorted(carried):
        loop_params.append(LeanParam(name=v, type=hole_type))

    init_args = [iter_expr] + [LeanIdent(v) for v in sorted(carried)]
    loop_call_init: LeanExpr = LeanIdent("loop")
    for a in init_args:
        loop_call_init = LeanApp(func=loop_call_init, arg=a)

    return LeanLet(
        name="loop",
        params=loop_params,
        type=LeanHole(),
        value=match,
        body=loop_call_init,
        is_rec=True,
    )


def _fold_for(s: PyFor, result: LeanExpr) -> LeanExpr:
    target = _assign_target_name(s.target)
    carried = _find_carried_vars(s.body, context="for")
    if (
        isinstance(s.iter, PyCall)
        and isinstance(s.iter.func, PyName)
        and s.iter.func.id == "range"
    ):
        return _make_for_range_loop(target, s.iter.args, s.body, carried, result)
    else:
        return _make_for_list_loop(
            target, _expr_to_lean(s.iter), s.body, carried, result
        )


_STMT_FOLD = {
    PyAnnAssign: _fold_assign_like,
    PyAssign: _fold_assign_like,
    PyAugAssign: _fold_aug_assign,
    PyIf: _fold_if,
    PyWhile: _fold_while,
    PyFor: _fold_for,
}


def _stmts_to_lean_expr(stmts: list[PyStmt]) -> LeanExpr:
    if not stmts:
        return LeanUnit()
    if len(stmts) == 1:
        return _stmt_to_expr(stmts[0])
    result = _stmt_to_expr(stmts[-1])
    for s in reversed(stmts[:-1]):
        handler = _STMT_FOLD.get(type(s))
        if handler:
            result = handler(s, result)
        else:
            s_expr = _stmt_to_expr(s)
            if not isinstance(s_expr, LeanUnit):
                result = LeanLet(
                    name="_", params=[], type=None, value=s_expr, body=result
                )
    return result


# ── Dispatch handlers for _stmt_to_expr ──────────────────────────────


def _expr_return(node: PyReturn) -> LeanExpr:
    if node.value:
        return _expr_to_lean(node.value)
    return LeanUnit()


def _expr_stmt_expr(node: PyExprStmt) -> LeanExpr:
    return _expr_to_lean(node.expr)


def _expr_if_stmt(node: PyIf) -> LeanExpr:
    test = _to_bool(_expr_to_lean(node.test), node.test)
    then_branch = _stmts_to_lean_expr(node.body)
    else_branch = _stmts_to_lean_expr(node.orelse) if node.orelse else LeanUnit()
    return LeanIf(cond=test, then_expr=then_branch, else_expr=else_branch)


def _expr_for_stmt(node: PyFor) -> LeanExpr:
    return _fold_for(node, LeanUnit())


def _expr_match_stmt(node: PyMatch) -> LeanExpr:
    subject = _expr_to_lean(node.subject)
    arms = []
    for case in node.cases:
        pat = _py_pat_to_lean(case.pattern)
        rhs = _stmts_to_lean_expr(case.body) if case.body else LeanUnit()
        arms.append(LeanMatchArm(pattern=pat, rhs=rhs))
    return LeanMatch(expr=subject, arms=arms)


def _expr_assign(node) -> LeanExpr:
    value = (
        _expr_to_lean(node.value)
        if hasattr(node, "value") and node.value
        else LeanUnit()
    )
    if isinstance(node, PyAnnAssign) and not node.value:
        return LeanUnit()
    target = _assign_target_name(node.target) if hasattr(node, "target") else "_"
    if isinstance(node.target, PySubscript):
        value = _make_subscript_assign(node.target, value)
    return LeanLet(
        name=_escape_name(target),
        params=[],
        type=None,
        value=value,
        body=LeanUnit(),
    )


def _expr_aug_assign(node: PyAugAssign) -> LeanExpr:
    target = _assign_target_name(node.target)
    op = _strip_aug_op(node.op)
    target_expr = _expr_to_lean(node.target)
    value = _expr_to_lean(node.value)
    binop = LeanBinOp(left=target_expr, op=op, right=value)
    if isinstance(node.target, PySubscript):
        value = _make_subscript_assign(node.target, binop)
    else:
        value = binop
    return LeanLet(
        name=_escape_name(target), params=[], type=None, value=value, body=LeanUnit()
    )


def _collect_name_refs(expr: PyExpr) -> set[str]:
    refs: set[str] = set()
    if isinstance(expr, PyName):
        refs.add(expr.id)
    elif isinstance(expr, PyBinOp):
        refs.update(_collect_name_refs(expr.left))
        refs.update(_collect_name_refs(expr.right))
    elif isinstance(expr, PyUnaryOp):
        refs.update(_collect_name_refs(expr.operand))
    elif isinstance(expr, PyCompare):
        refs.update(_collect_name_refs(expr.left))
        for c in expr.comparators:
            refs.update(_collect_name_refs(c))
    elif isinstance(expr, PyBoolOp):
        for v in expr.values:
            refs.update(_collect_name_refs(v))
    elif isinstance(expr, PyCall):
        refs.update(_collect_name_refs(expr.func))
        for a in expr.args:
            refs.update(_collect_name_refs(a))
    elif isinstance(expr, PyAttribute):
        refs.update(_collect_name_refs(expr.value))
    elif isinstance(expr, PySubscript):
        refs.update(_collect_name_refs(expr.value))
        refs.update(_collect_name_refs(expr.slice))
    return refs


def _find_carried_vars(
    body: list[PyStmt], test: PyExpr | None = None, context: str = "while"
) -> set[str]:
    assign_targets: set[str] = set()

    def _collect_assigns(stmt: PyStmt) -> None:
        nonlocal assign_targets
        if isinstance(stmt, (PyAssign, PyAugAssign)):
            target = _assign_target_name(stmt.target)
            if target:
                assign_targets.add(target)
        elif isinstance(stmt, PyIf):
            for s in stmt.body:
                _collect_assigns(s)
            for s in stmt.orelse:
                _collect_assigns(s)
        elif isinstance(stmt, PyWhile):
            for s in stmt.body:
                _collect_assigns(s)

    for stmt in body:
        _collect_assigns(stmt)

    if not assign_targets:
        return set()

    carried: set[str] = set()
    seen_assigned: set[str] = set()

    def _scan_refs(expr: PyExpr) -> None:
        for r in _collect_name_refs(expr):
            if r in assign_targets and r not in seen_assigned:
                carried.add(r)

    def _visit_refs(stmt: PyStmt) -> None:
        nonlocal carried, seen_assigned
        if isinstance(stmt, PyAugAssign):
            target = _assign_target_name(stmt.target)
            if target:
                if context != "for" or target not in seen_assigned:
                    carried.add(target)
                _scan_refs(stmt.value) if stmt.value else None
                seen_assigned.add(target)
        elif isinstance(stmt, (PyAssign, PyAnnAssign)):
            target = _assign_target_name(stmt.target)
            if target:
                if isinstance(stmt.target, PySubscript):
                    carried.add(target)
                val = stmt.value if hasattr(stmt, "value") else None
                _scan_refs(val) if val else None
                seen_assigned.add(target)
        elif isinstance(stmt, PyIf):
            _scan_refs(stmt.test)
            for s in stmt.body:
                _visit_refs(s)
            for s in stmt.orelse:
                _visit_refs(s)
        elif isinstance(stmt, PyWhile):
            _scan_refs(stmt.test)
            for s in stmt.body:
                _visit_refs(s)
        elif isinstance(stmt, PyExprStmt):
            _scan_refs(stmt.expr)
        elif isinstance(stmt, PyReturn) and stmt.value:
            _scan_refs(stmt.value)

    if test is not None:
        _scan_refs(test)

    for stmt in body:
        _visit_refs(stmt)

    return carried


def _tail_reaches_unit(expr: LeanExpr, carried: set[str]) -> bool:
    if isinstance(expr, LeanUnit):
        return True
    if isinstance(expr, LeanLet) and expr.name not in carried:
        return _tail_reaches_unit(expr.body, carried)
    return False


def _is_loop_call(expr: LeanExpr, loop_name: str = "loop") -> bool:
    while isinstance(expr, LeanApp):
        if isinstance(expr.func, LeanIdent) and expr.func.name == loop_name:
            return True
        if isinstance(expr.func, LeanApp):
            expr = expr.func
        else:
            break
    return False


def _make_loop_call(all_carried: set[str], loop_name: str = "loop") -> LeanExpr:
    sorted_names = sorted(all_carried)
    call: LeanExpr = LeanIdent(loop_name)
    for n in sorted_names:
        call = LeanApp(func=call, arg=LeanIdent(n))
    return call


def _ensure_leaf_loop_call(
    expr: LeanExpr, all_carried: set[str], loop_name: str = "loop"
) -> LeanExpr:
    if isinstance(expr, LeanIf):
        return LeanIf(
            cond=expr.cond,
            then_expr=_ensure_leaf_loop_call(expr.then_expr, all_carried, loop_name),
            else_expr=_ensure_leaf_loop_call(expr.else_expr, all_carried, loop_name)
            if expr.else_expr
            else None,
        )
    if _is_loop_call(expr, loop_name):
        return expr
    # If it's already a call to some function, it's a valid leaf
    if isinstance(expr, LeanApp):
        inner = expr
        while isinstance(inner, LeanApp):
            inner = inner.func
        if isinstance(inner, LeanIdent):
            return expr
    loop_call = _make_loop_call(all_carried, loop_name)
    if isinstance(expr, LeanUnit):
        return loop_call
    if isinstance(expr, LeanLet):
        return _append_continuation(expr, loop_call)
    return _append_continuation(
        LeanLet(name="_", params=[], type=None, value=expr, body=LeanUnit()),
        loop_call,
    )


def _substitute_var(expr: LeanExpr, var: str, replacement: LeanExpr) -> LeanExpr:
    """Substitute all occurrences of LeanIdent(var) with replacement."""
    if isinstance(expr, LeanIdent) and expr.name == var:
        return replacement
    if isinstance(expr, LeanApp):
        return LeanApp(
            func=_substitute_var(expr.func, var, replacement),
            arg=_substitute_var(expr.arg, var, replacement),
        )
    if isinstance(expr, LeanBinOp):
        return LeanBinOp(
            left=_substitute_var(expr.left, var, replacement),
            op=expr.op,
            right=_substitute_var(expr.right, var, replacement),
        )
    if isinstance(expr, LeanUnaryOp):
        return LeanUnaryOp(
            op=expr.op,
            operand=_substitute_var(expr.operand, var, replacement),
        )
    if isinstance(expr, LeanIf):
        return LeanIf(
            cond=_substitute_var(expr.cond, var, replacement),
            then_expr=_substitute_var(expr.then_expr, var, replacement),
            else_expr=_substitute_var(expr.else_expr, var, replacement)
            if expr.else_expr
            else None,
        )
    if isinstance(expr, LeanLet):
        return LeanLet(
            name=expr.name,
            params=expr.params,
            type=expr.type,
            value=_substitute_var(expr.value, var, replacement) if expr.value else None,
            body=_substitute_var(expr.body, var, replacement),
            is_mut=expr.is_mut,
            is_rec=expr.is_rec,
        )
    if isinstance(expr, LeanMatch):
        return LeanMatch(
            expr=_substitute_var(expr.expr, var, replacement),
            arms=[
                LeanMatchArm(
                    pattern=arm.pattern,
                    rhs=_substitute_var(arm.rhs, var, replacement),
                )
                for arm in expr.arms
            ],
        )
    if isinstance(expr, LeanLambda):
        return LeanLambda(
            params=expr.params,
            body=_substitute_var(expr.body, var, replacement),
        )
    if isinstance(expr, LeanProj):
        return LeanProj(
            expr=_substitute_var(expr.expr, var, replacement),
            field=expr.field,
        )
    if isinstance(expr, LeanTypeSpec):
        return LeanTypeSpec(
            expr=_substitute_var(expr.expr, var, replacement),
            type=_substitute_var(expr.type, var, replacement),
        )
    return expr


def _replace_carried_assign(
    expr: LeanExpr,
    carried: set[str],
    loop_name: str = "loop",
    all_carried: set[str] | None = None,
) -> LeanExpr:
    if all_carried is None:
        all_carried = carried

    if isinstance(expr, LeanLet) and expr.name in carried:
        new_values: dict[str, LeanExpr] = {}
        collected_order: list[str] = []
        remaining: LeanExpr = expr
        while isinstance(remaining, LeanLet) and remaining.name in carried:
            new_values[remaining.name] = remaining.value
            collected_order.append(remaining.name)
            remaining = remaining.body
        if not _tail_reaches_unit(remaining, carried):
            return LeanLet(
                name=expr.name,
                params=expr.params,
                type=expr.type,
                value=_replace_carried_assign(
                    expr.value, carried, loop_name, all_carried
                ),
                body=_replace_carried_assign(
                    expr.body, carried, loop_name, all_carried
                ),
                is_mut=expr.is_mut,
                is_rec=expr.is_rec,
            )
        # Dependency-order substitution: substitute earlier-assigned vars'
        # new values into later-assigned vars' expressions, preserving
        # Python's sequential assignment semantics.
        substituted: dict[str, LeanExpr] = {}
        for name in collected_order:
            val = new_values[name]
            for prev_name in substituted:
                val = _substitute_var(val, prev_name, substituted[prev_name])
            substituted[name] = val
        sorted_names = sorted(all_carried)
        call: LeanExpr = LeanIdent(loop_name)
        for n in sorted_names:
            if n in substituted:
                call = LeanApp(func=call, arg=substituted[n])
            else:
                call = LeanApp(func=call, arg=LeanIdent(n))
        return call
    elif isinstance(expr, LeanLet):
        return LeanLet(
            name=expr.name,
            params=expr.params,
            type=expr.type,
            value=_replace_carried_assign(expr.value, carried, loop_name, all_carried),
            body=_replace_carried_assign(expr.body, carried, loop_name, all_carried),
            is_mut=expr.is_mut,
            is_rec=expr.is_rec,
        )
    elif isinstance(expr, LeanIf):
        then_expr = _replace_carried_assign(
            expr.then_expr, carried, loop_name, all_carried
        )
        else_expr = (
            _replace_carried_assign(expr.else_expr, carried, loop_name, all_carried)
            if expr.else_expr
            else None
        )
        return LeanIf(
            cond=_replace_carried_assign(expr.cond, carried, loop_name, all_carried),
            then_expr=_ensure_leaf_loop_call(then_expr, all_carried, loop_name),
            else_expr=_ensure_leaf_loop_call(else_expr, all_carried, loop_name)
            if else_expr is not None
            else None,
        )
    elif isinstance(expr, LeanContinue):
        call: LeanExpr = LeanIdent(loop_name)
        for n in sorted(all_carried):
            call = LeanApp(func=call, arg=LeanIdent(n))
        return call
    elif isinstance(expr, LeanApp):
        return LeanApp(
            func=_replace_carried_assign(expr.func, carried, loop_name, all_carried),
            arg=_replace_carried_assign(expr.arg, carried, loop_name, all_carried),
        )
    elif isinstance(expr, LeanBinOp):
        return LeanBinOp(
            left=_replace_carried_assign(expr.left, carried, loop_name, all_carried),
            op=expr.op,
            right=_replace_carried_assign(expr.right, carried, loop_name, all_carried),
        )
    return expr


def _expr_while_stmt(node: PyWhile) -> LeanExpr:
    is_infinite = isinstance(node.test, PyConstant) and node.test.value is True
    carried = _find_carried_vars(node.body, node.test)
    body = _stmts_to_lean_expr(node.body)
    body = _replace_carried_assign(body, carried, "while_loop")
    if not is_infinite:
        test = _to_bool(_expr_to_lean(node.test), node.test)
        body = LeanIf(cond=test, then_expr=body, else_expr=LeanUnit())

    hole_type = LeanIdent("Nat") if USE_NAT else LeanHole()
    loop_params = [LeanParam(name=v, type=hole_type) for v in sorted(carried)]
    init_args = [LeanIdent(v) for v in sorted(carried)]

    result: LeanExpr = LeanUnit()
    if len(init_args) == 1:
        result = LeanApp(func=LeanIdent("while_loop"), arg=init_args[0])
    elif len(init_args) > 1:
        result = LeanApp(func=LeanIdent("while_loop"), arg=init_args[0])
        for a in init_args[1:]:
            result = LeanApp(func=result, arg=a)

    if not carried:
        return body

    return LeanLet(
        name="while_loop",
        params=loop_params,
        type=hole_type,
        value=body,
        body=result,
        is_rec=True,
    )


def _expr_break_stmt(node: PyBreak) -> LeanExpr:
    return LeanBreak()


def _expr_continue_stmt(node: PyContinue) -> LeanExpr:
    return LeanContinue()


_STMT_TO_EXPR = {
    PyReturn: _expr_return,
    PyExprStmt: _expr_stmt_expr,
    PyIf: _expr_if_stmt,
    PyFor: _expr_for_stmt,
    PyMatch: _expr_match_stmt,
    PyAssign: _expr_assign,
    PyAnnAssign: _expr_assign,
    PyAugAssign: _expr_aug_assign,
    PyWhile: _expr_while_stmt,
    PyBreak: _expr_break_stmt,
    PyContinue: _expr_continue_stmt,
}


def _stmt_to_expr(node: PyStmt) -> LeanExpr:
    handler = _STMT_TO_EXPR.get(type(node))
    if handler:
        return handler(node)
    return LeanUnit()


# ── Dispatch handlers for _expr_to_lean ──────────────────────────────


def _expr_name(node: PyName) -> LeanExpr:
    name = _escape_name(node.id)
    if name == "None":
        return LeanIdent("none")
    elif name == "True":
        return LeanBool(True)
    elif name == "False":
        return LeanBool(False)
    return LeanIdent(name)


def _expr_constant(node: PyConstant) -> LeanExpr:
    if node.value is None:
        return LeanIdent("none")
    elif isinstance(node.value, bool):
        return LeanBool(node.value)
    elif isinstance(node.value, int):
        return LeanNum(value=node.value)
    elif isinstance(node.value, float):
        return LeanFloat(value=node.value)
    elif isinstance(node.value, str):
        return LeanString(value=node.value)
    return LeanNum(value=int(node.value))


def _expr_binop(node: PyBinOp) -> LeanExpr:
    left = _expr_to_lean(node.left)
    right = _expr_to_lean(node.right)
    op_map = {
        "+": "+",
        "-": "-",
        "*": "*",
        "/": "/",
        "//": "/",
        "%": "%",
        "**": "^",
        "==": "=",
        "!=": "≠",
        "<": "<",
        "<=": "≤",
        ">": ">",
        ">=": "≥",
        "and": "∧",
        "or": "∨",
        "|": "|||",
        "&": "&&&",
        "^": "^^^",
        "<<": "<<<",
        ">>": ">>>",
    }
    op_lean = op_map.get(node.op, node.op)
    if node.op == "**" and (
        isinstance(node.right, PyConstant) and isinstance(node.right.value, float)
    ):
        left = LeanTypeSpec(expr=left, type=LeanIdent("Float"))
    return LeanBinOp(left=left, op=op_lean, right=right)


def _expr_unary_op(node: PyUnaryOp) -> LeanExpr:
    operand = _expr_to_lean(node.operand)
    if node.op == "-":
        return LeanApp(func=LeanIdent("neg"), arg=operand)
    elif node.op == "not":
        return LeanApp(func=LeanIdent("not"), arg=operand)
    return LeanApp(func=LeanIdent(node.op), arg=operand)


def _expr_compare(node: PyCompare) -> LeanExpr:
    left = _expr_to_lean(node.left)
    for i, op in enumerate(node.ops):
        right = _expr_to_lean(node.comparators[i])
        cmp_map = {
            "==": "==",
            "!=": "!=",
            "<": "<",
            "<=": "≤",
            ">": ">",
            ">=": "≥",
            "is": "==",
            "is not": "!=",
            "in": "∈",
        }
        cmp_op = cmp_map.get(op, op)
        left = LeanBinOp(left=left, op=cmp_op, right=right)
    return left


def _expr_bool_op(node: PyBoolOp) -> LeanExpr:
    values = [_expr_to_lean(v) for v in node.values]
    op_lean = "∧" if node.op == "and" else "∨"
    result = values[0]
    for v in values[1:]:
        result = LeanBinOp(left=result, op=op_lean, right=v)
    return result


# -- Stdlib pattern mapping table ----------------------------------------
# Each entry is a tuple (matcher, builder) where:
#   matcher :: (PyCall) -> dict[str, PyExpr] | None
#   builder :: (dict)  -> LeanExpr
# The dict maps placeholder names to the captured PyExpr nodes.

_STDLIB_MAP: list[tuple] = []


def _stdlib_register(matcher):
    """Decorator to register a stdlib pattern matcher."""
    _STDLIB_MAP.append(matcher)
    return matcher


@_stdlib_register
def _match_pow(node: PyCall) -> dict | None:
    """pow(x, y) -> x ^ y"""
    if (
        isinstance(node.func, PyName)
        and node.func.id == "pow"
        and len(node.args) == 2
    ):
        return {"base": node.args[0], "exp": node.args[1]}
    return None


def _build_pow(match: dict) -> LeanExpr:
    return LeanBinOp(
        left=_expr_to_lean(match["base"]),
        op="^",
        right=_expr_to_lean(match["exp"]),
    )


@_stdlib_register
def _match_bin_count(node: PyCall) -> dict | None:
    """bin(x).count("1") -> Nat.popCount x"""
    if (
        isinstance(node.func, PyAttribute)
        and node.func.attr == "count"
        and isinstance(node.func.value, PyCall)
        and isinstance(node.func.value.func, PyName)
        and node.func.value.func.id == "bin"
        and len(node.func.value.args) == 1
        and len(node.args) == 1
        and isinstance(node.args[0], PyConstant)
        and node.args[0].value in ("1", 1)
    ):
        return {"x": node.func.value.args[0]}
    return None


def _build_bin_count(match: dict) -> LeanExpr:
    global _uses_popcount
    _uses_popcount = True
    return LeanApp(func=LeanIdent("Nat.popCount"), arg=_expr_to_lean(match["x"]))


@_stdlib_register
def _match_math_factorial(node: PyCall) -> dict | None:
    """math.factorial(x) -> Nat.factorial x"""
    if (
        isinstance(node.func, PyAttribute)
        and node.func.attr == "factorial"
        and isinstance(node.func.value, PyName)
        and node.func.value.id == "math"
        and len(node.args) == 1
    ):
        return {"x": node.args[0]}
    return None


_FACTORIAL_FALLBACK_SOURCE = """
def factorial(n: int) -> int:
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result
"""


def _transpile_func_source(source: str) -> LeanDef | None:
    """Parse and transpile a single Python function definition string."""
    try:
        mod = parse_python(source)
        for stmt in mod.body:
            if isinstance(stmt, PyFunctionDef):
                return _func_to_lean(stmt)
    except Exception:
        return None
    return None


def _build_math_factorial(match: dict) -> LeanExpr:
    global _transpiling_helper
    if _transpiling_helper:
        return LeanApp(func=LeanIdent("Nat.factorial"), arg=_expr_to_lean(match["x"]))

    func_obj = _imported_modules.get("math")
    if func_obj is not None:
        try:
            source = inspect.getsource(getattr(func_obj, "factorial"))
            _transpiling_helper = True
            lean_def = _transpile_func_source(source)
            _transpiling_helper = False
            if lean_def is not None:
                _generated_helpers.append(lean_def)
                return LeanApp(func=LeanIdent("factorial"), arg=_expr_to_lean(match["x"]))
        except (OSError, TypeError):
            _transpiling_helper = False

    _transpiling_helper = True
    lean_def = _transpile_func_source(_FACTORIAL_FALLBACK_SOURCE)
    _transpiling_helper = False
    if lean_def is not None:
        _generated_helpers.append(lean_def)
        return LeanApp(func=LeanIdent("factorial"), arg=_expr_to_lean(match["x"]))
    return LeanApp(func=LeanIdent("Nat.factorial"), arg=_expr_to_lean(match["x"]))


@_stdlib_register
def _match_bit_count(node: PyCall) -> dict | None:
    """x.bit_count() -> Nat.popCount x"""
    if (
        isinstance(node.func, PyAttribute)
        and node.func.attr == "bit_count"
        and len(node.args) == 0
    ):
        return {"x": node.func.value}
    return None


def _build_bit_count(match: dict) -> LeanExpr:
    global _uses_popcount
    _uses_popcount = True
    return LeanApp(func=LeanIdent("Nat.popCount"), arg=_expr_to_lean(match["x"]))


# -- End stdlib mapping table -------------------------------------------


def _stdlib_expr_call(node: PyCall) -> LeanExpr | None:
    """Check registered stdlib patterns; return Lean expr or None."""
    for matcher in _STDLIB_MAP:
        match = matcher(node)
        if match is not None:
            builder_name = matcher.__name__.replace("_match_", "_build_")
            builder = globals().get(builder_name)
            if builder:
                return builder(match)
    return None


def _expr_call(node: PyCall) -> LeanExpr:
    # Check stdlib patterns first
    stdlib_result = _stdlib_expr_call(node)
    if stdlib_result is not None:
        return stdlib_result

    if isinstance(node.func, PyName) and node.func.id == "int" and len(node.args) == 1:
        arg = _expr_to_lean(node.args[0])
        return LeanApp(func=LeanIdent("Float.floor"), arg=arg)
    if isinstance(node.func, PyName) and node.func.id == "len" and len(node.args) == 1:
        arg = _expr_to_lean(node.args[0])
        return LeanApp(func=LeanIdent("List.length"), arg=arg)
    func = _expr_to_lean(node.func)
    args = [_expr_to_lean(a) for a in node.args]
    kwargs = [(k, _expr_to_lean(v)) for k, v in node.kwargs]
    result = func
    for a in args:
        result = LeanApp(func=result, arg=a)
    for k, v in kwargs:
        result = LeanApp(func=result, arg=LeanNamedArg(name=k, value=v))
    return result


def _expr_if_exp(node: PyIfExp) -> LeanExpr:
    test = _to_bool(_expr_to_lean(node.test), node.test)
    body = _expr_to_lean(node.body)
    orelse = _expr_to_lean(node.orelse)
    return LeanIf(cond=test, then_expr=body, else_expr=orelse)


def _expr_attr(node: PyAttribute) -> LeanExpr:
    return LeanProj(expr=_expr_to_lean(node.value), field=node.attr)


_uses_subscript: bool = False


def _expr_subscript(node: PySubscript) -> LeanExpr:
    global _uses_subscript
    _uses_subscript = True
    return LeanApp(
        func=LeanApp(func=LeanIdent("get"), arg=_expr_to_lean(node.value)),
        arg=_expr_to_lean(node.slice),
    )


def _expr_tuple(node: PyTuple) -> LeanExpr:
    elts = [_expr_to_lean(e) for e in node.elts]
    if not elts:
        return LeanUnit()
    result = elts[0]
    for e in elts[1:]:
        result = LeanApp(func=LeanApp(func=LeanIdent("Prod.mk"), arg=result), arg=e)
    return result


def _expr_dict(node: PyDict) -> LeanExpr:
    keys = [_expr_to_lean(k) for k in node.keys if k]
    values = [_expr_to_lean(v) for v in node.values]
    result = LeanIdent("HashMap.empty")
    for k, v in zip(reversed(keys), reversed(values)):
        result = LeanApp(
            func=LeanApp(
                func=LeanApp(func=LeanIdent("HashMap.insert"), arg=result), arg=k
            ),
            arg=v,
        )
    return result


def _expr_lambda(node: PyLambda) -> LeanExpr:
    args = [
        (arg_name, _py_type_to_lean_type(ann) if ann else None)
        for arg_name, ann in node.args
    ]
    params = [LeanParam(name=_escape_name(n), type=t) for n, t in args]
    body = _expr_to_lean(node.body)
    return LeanLambda(params=params, body=body)


def _expr_starred(node: PyStarred) -> LeanExpr:
    return _expr_to_lean(node.value)


def _expr_walrus(node: PyWalrus) -> LeanExpr:
    return _expr_to_lean(node.value)


_EXPR_TO_LEAN = {
    PyName: _expr_name,
    PyConstant: _expr_constant,
    PyBinOp: _expr_binop,
    PyUnaryOp: _expr_unary_op,
    PyCompare: _expr_compare,
    PyBoolOp: _expr_bool_op,
    PyCall: _expr_call,
    PyIfExp: _expr_if_exp,
    PyAttribute: _expr_attr,
    PySubscript: _expr_subscript,
    PyList: _expr_list,
    PyTuple: _expr_tuple,
    PyDict: _expr_dict,
    PyLambda: _expr_lambda,
    PyStarred: _expr_starred,
    PyWalrus: _expr_walrus,
}


def _expr_to_lean(node: PyExpr) -> LeanExpr:
    if node is None:
        return LeanUnit()
    handler = _EXPR_TO_LEAN.get(type(node))
    if handler:
        return handler(node)
    return LeanHole()


# ── Dispatch handlers for _py_type_to_lean_type ──────────────────────


def _type_name(node: PyName) -> LeanExpr:
    name = node.id
    if name == "None":
        return LeanIdent("Unit")
    elif name == "int":
        return LeanIdent("Nat") if USE_NAT else LeanIdent("Int")
    elif name == "float":
        return LeanIdent("Float")
    elif name == "bool":
        return LeanIdent("Bool")
    elif name == "str":
        return LeanIdent("String")
    elif name == "bytes":
        return LeanIdent("ByteArray")
    elif name == "list":
        return LeanApp(func=LeanIdent("List"), arg=LeanHole())
    elif name == "dict":
        return LeanApp(
            func=LeanApp(func=LeanIdent("HashMap"), arg=LeanHole()), arg=LeanHole()
        )
    elif name == "set":
        return LeanApp(func=LeanIdent("Set"), arg=LeanHole())
    elif name == "tuple":
        return LeanIdent("Prod")
    elif name == "Any":
        return LeanSort()
    return LeanIdent(name)


def _type_subscript(node: PySubscript) -> LeanExpr:
    value = _py_type_to_lean_type(node.value)
    slice_val = _py_type_to_lean_type(node.slice)
    if isinstance(node.value, PyName):
        base = node.value.id
        if base in ("list", "List"):
            return LeanApp(func=LeanIdent("List"), arg=slice_val)
        elif base in ("dict", "Dict"):
            return LeanApp(
                func=LeanApp(func=LeanIdent("HashMap"), arg=LeanHole()),
                arg=slice_val,
            )
        elif base in ("tuple", "Tuple"):
            if isinstance(node.slice, PyTuple):
                elts = [_py_type_to_lean_type(e) for e in node.slice.elts]
                result = elts[0]
                for e in elts[1:]:
                    result = LeanApp(
                        func=LeanApp(func=LeanIdent("Prod"), arg=result), arg=e
                    )
                return result
            return LeanApp(
                func=LeanIdent("Prod"), arg=_py_type_to_lean_type(node.slice)
            )
        elif base in ("optional", "Optional"):
            return LeanApp(func=LeanIdent("Option"), arg=slice_val)
        elif base in ("set", "Set"):
            return LeanApp(func=LeanIdent("Set"), arg=slice_val)
        return LeanApp(func=LeanIdent(base), arg=slice_val)
    return LeanApp(func=value, arg=slice_val)


def _type_attribute(node: PyAttribute) -> LeanExpr:
    return LeanProj(expr=_py_type_to_lean_type(node.value), field=node.attr)


def _type_constant(node: PyConstant) -> LeanExpr:
    if isinstance(node.value, str):
        return LeanIdent(node.value)
    return LeanHole()


_TYPE_TO_LEAN = {
    PyName: _type_name,
    PySubscript: _type_subscript,
    PyAttribute: _type_attribute,
    PyConstant: _type_constant,
}


def _py_type_to_lean_type(node: PyExpr) -> LeanExpr:
    handler = _TYPE_TO_LEAN.get(type(node))
    if handler:
        return handler(node)
    return LeanHole()
