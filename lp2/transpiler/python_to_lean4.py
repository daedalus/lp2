from typing import Optional
from lp2.ast.python_ast import *
from lp2.ast.lean4_ast import *


_PY_TYPE_TO_LEAN = {
    'int': LeanIdent('Int'),
    'float': LeanIdent('Float'),
    'bool': LeanIdent('Bool'),
    'str': LeanIdent('String'),
    'bytes': LeanIdent('ByteArray'),
    'None': LeanIdent('Unit'),
    'list': LeanIdent('List'),
    'tuple': LeanIdent('Prod'),
    'dict': LeanIdent('HashMap'),
    'set': LeanIdent('Set'),
}


_LEAN_TYPE_KW = {
    'Nat': 'Nat', 'Int': 'Int', 'Float': 'Float', 'Bool': 'Bool',
    'String': 'String', 'Char': 'Char', 'Unit': 'Unit',
    'List': 'List', 'Option': 'Option', 'Prod': 'Prod',
}


_NAME_ESCAPE = {
    'def': 'def_', 'match': 'match_', 'if': 'if_', 'else': 'else_',
    'then': 'then_', 'let': 'let_', 'in': 'in_', 'do': 'do_',
    'for': 'for_', 'while': 'while_', 'class': 'class_',
    'try': 'try_', 'except': 'except_', 'raise': 'raise_',
    'with': 'with_', 'return': 'return_', 'and': 'and_', 'or': 'or_',
    'not': 'not_', 'true': 'true_', 'false': 'false_',
    'instance': 'instance_', 'open': 'open_',
}


def _escape_name(name: str) -> str:
    return _NAME_ESCAPE.get(name, name)


def py_to_lean(node: PyNode) -> LeanNode:
    if isinstance(node, PyModule):
        body = []
        for stmt in node.body:
            lean_cmd = _stmt_to_lean_cmd(stmt)
            if lean_cmd:
                body.append(lean_cmd)
        return LeanModule(imports=[], body=body)
    raise ValueError(f"Unknown node: {type(node).__name__}")


def _stmt_to_lean_cmd(node: PyStmt) -> Optional[LeanCommand]:
    if isinstance(node, PyFunctionDef):
        return _func_to_lean(node)
    elif isinstance(node, PyClassDef):
        return _class_to_lean(node)
    elif isinstance(node, PyAssign) or isinstance(node, PyAnnAssign):
        return _assign_to_lean(node)
    elif isinstance(node, PyImport):
        return LeanOpen(names=[n.split('.')[-1] for n in node.names])
    elif isinstance(node, PyExprStmt):
        if isinstance(node.expr, PyCall) and isinstance(node.expr.func, PyName) and node.expr.func.id in ('print', 'eval'):
            if node.expr.func.id == 'print':
                return LeanExample(expr=_call_to_lean_print(node.expr))
            return LeanExample(expr=_expr_to_lean(node.expr.args[0]) if node.expr.args else LeanUnit())
        return LeanExample(expr=_expr_to_lean(node.expr))
    return None


def _func_to_lean(node: PyFunctionDef) -> LeanDef:
    name = _escape_name(node.name)
    params = []
    for arg_name, annotation, default in node.args:
        lean_ann = None
        if annotation:
            lean_ann = _py_type_to_lean_type(annotation)
        kwargs = {}
        if default is not None:
            kwargs['default'] = _expr_to_lean(default)
        params.append(LeanParam(name=_escape_name(arg_name), type=lean_ann, **kwargs))

    return_type = None
    if node.return_type:
        return_type = _py_type_to_lean_type(node.return_type)
    else:
        return_type = LeanIdent('Unit')

    if len(node.body) == 1 and isinstance(node.body[0], PyReturn):
        body = _expr_to_lean(node.body[0].value) if node.body[0].value else LeanIdent('Unit')
    else:
        body = _stmts_to_lean_expr(node.body)

    return LeanDef(name=name, params=params, return_type=return_type, value=body)


def _class_to_lean(node: PyClassDef) -> LeanStructure:
    name = _escape_name(node.name)
    fields = []
    for stmt in node.body:
        if isinstance(stmt, PyAnnAssign) or isinstance(stmt, PyAssign):
            field_name = _get_field_name(stmt.target)
            if field_name:
                ann = stmt.annotation if isinstance(stmt, PyAnnAssign) else None
                lean_ann = _py_type_to_lean_type(ann) if ann else None
                fields.append(LeanParam(name=_escape_name(field_name), type=lean_ann or LeanHole()))
    return LeanStructure(name=name, params=[], extends=[], fields=fields)


def _get_field_name(node: PyExpr) -> Optional[str]:
    if isinstance(node, PyName):
        return node.id
    return None


def _assign_to_lean(node) -> Optional[LeanCommand]:
    return None


def _stmts_to_lean_expr(stmts: list[PyStmt]) -> LeanExpr:
    if not stmts:
        return LeanUnit()
    if len(stmts) == 1:
        return _stmt_to_expr(stmts[0])
    result = _stmt_to_expr(stmts[-1])
    for s in reversed(stmts[:-1]):
        if isinstance(s, PyAnnAssign) or isinstance(s, PyAssign):
            target = _assign_target_name(s.target)
            value = _expr_to_lean(s.value)
            result = LeanLet(name=_escape_name(target), params=[], type=None,
                             value=value, body=result)
        elif isinstance(s, PyIf):
            test = _expr_to_lean(s.test)
            then_body = _stmts_to_lean_expr(s.body) if s.body else LeanUnit()
            if s.orelse:
                else_body = _stmts_to_lean_expr(s.orelse)
            else:
                else_body = result
            result = LeanIf(cond=test, then_expr=then_body, else_expr=else_body)
        else:
            s_expr = _stmt_to_expr(s)
            if not isinstance(s_expr, LeanUnit):
                result = LeanLet(name='_', params=[], type=None, value=s_expr, body=result)
    return result


def _stmt_to_expr(node: PyStmt) -> LeanExpr:
    if isinstance(node, PyReturn):
        if node.value:
            return _expr_to_lean(node.value)
        return LeanUnit()
    elif isinstance(node, PyExprStmt):
        return _expr_to_lean(node.expr)
    elif isinstance(node, PyIf):
        test = _expr_to_lean(node.test)
        then_branch = _stmts_to_lean_expr(node.body)
        else_branch = _stmts_to_lean_expr(node.orelse) if node.orelse else None
        return LeanIf(cond=test, then_expr=then_branch, else_expr=else_branch)
    elif isinstance(node, PyFor):
        target = _expr_to_lean(node.target)
        iter_expr = _expr_to_lean(node.iter)
        body = _stmts_to_lean_expr(node.body)
        return LeanApp(func=LeanApp(func=LeanIdent('for_in'), arg=iter_expr),
                       arg=LeanLambda(params=[LeanParam(name='_', type=None)], body=body))
    elif isinstance(node, PyMatch):
        subject = _expr_to_lean(node.subject)
        arms = []
        for case in node.cases:
            pat = _py_pat_to_lean(case.pattern)
            rhs = _stmts_to_lean_expr(case.body) if case.body else LeanUnit()
            arms.append(LeanMatchArm(pattern=pat, rhs=rhs))
        return LeanMatch(expr=subject, arms=arms)
    elif isinstance(node, PyAssign) or isinstance(node, PyAnnAssign):
        target = _expr_to_lean(node.target)
        value = _expr_to_lean(node.value) if hasattr(node, 'value') and node.value else LeanUnit()
        if isinstance(node, PyAnnAssign) and not node.value:
            return LeanUnit()
        return value
    return LeanUnit()


def _expr_to_lean(node: PyExpr) -> LeanExpr:
    if node is None:
        return LeanUnit()
    if isinstance(node, PyName):
        name = _escape_name(node.id)
        if name == 'None':
            return LeanIdent('none')
        elif name == 'True':
            return LeanBool(True)
        elif name == 'False':
            return LeanBool(False)
        return LeanIdent(name)
    elif isinstance(node, PyConstant):
        if node.value is None:
            return LeanIdent('none')
        elif isinstance(node.value, bool):
            return LeanBool(node.value)
        elif isinstance(node.value, int):
            return LeanNum(value=node.value)
        elif isinstance(node.value, float):
            return LeanFloat(value=node.value)
        elif isinstance(node.value, str):
            return LeanString(value=node.value)
        return LeanNum(value=int(node.value))
    elif isinstance(node, PyBinOp):
        left = _expr_to_lean(node.left)
        right = _expr_to_lean(node.right)
        op_map = {
            '+': '+', '-': '-', '*': '*', '/': '/',
            '//': '/', '%': '%', '**': '^',
            '==': '=', '!=': '≠',
            '<': '<', '<=': '≤', '>': '>', '>=': '≥',
            'and': '∧', 'or': '∨',
            '|': '|||', '&': '&&&', '^': '^^^',
            '<<': '<<<', '>>': '>>>',
        }
        op_lean = op_map.get(node.op, node.op)
        return LeanBinOp(left=left, op=op_lean, right=right)
    elif isinstance(node, PyUnaryOp):
        operand = _expr_to_lean(node.operand)
        if node.op == '-':
            return LeanApp(func=LeanIdent('neg'), arg=operand)
        elif node.op == 'not':
            return LeanApp(func=LeanIdent('not'), arg=operand)
        return LeanApp(func=LeanIdent(node.op), arg=operand)
    elif isinstance(node, PyCompare):
        left = _expr_to_lean(node.left)
        for i, op in enumerate(node.ops):
            right = _expr_to_lean(node.comparators[i])
            cmp_map = {
                '==': '==', '!=': '!=',
                '<': '<', '<=': '≤', '>': '>', '>=': '≥',
                'is': '==', 'is not': '!=',
                'in': '∈',
            }
            cmp_op = cmp_map.get(op, op)
            left = LeanBinOp(left=left, op=cmp_op, right=right)
        return left
    elif isinstance(node, PyBoolOp):
        values = [_expr_to_lean(v) for v in node.values]
        if node.op == 'and':
            return LeanIf(cond=values[0], then_expr=values[1] if len(values) > 1 else values[0],
                         else_expr=LeanBool(False))
        elif node.op == 'or':
            return LeanIf(cond=values[0], then_expr=LeanBool(True),
                         else_expr=values[1] if len(values) > 1 else LeanBool(False))
    elif isinstance(node, PyCall):
        func = _expr_to_lean(node.func)
        args = [_expr_to_lean(a) for a in node.args]
        kwargs = [(k, _expr_to_lean(v)) for k, v in node.kwargs]
        result = func
        for a in args:
            result = LeanApp(func=result, arg=a)
        for k, v in kwargs:
            result = LeanApp(func=result, arg=LeanNamedArg(name=k, value=v))
        return result
    elif isinstance(node, PyIfExp):
        test = _expr_to_lean(node.test)
        body = _expr_to_lean(node.body)
        orelse = _expr_to_lean(node.orelse)
        return LeanIf(cond=test, then_expr=body, else_expr=orelse)
    elif isinstance(node, PyAttribute):
        return LeanProj(expr=_expr_to_lean(node.value), field=node.attr)
    elif isinstance(node, PySubscript):
        return LeanApp(func=LeanApp(func=LeanIdent('get'), arg=_expr_to_lean(node.value)),
                      arg=_expr_to_lean(node.slice))
    elif isinstance(node, PyList):
        elts = [_expr_to_lean(e) for e in node.elts]
        if not elts:
            return LeanIdent('List.nil')
        result: LeanExpr = LeanIdent(f'{_expr_to_lean(elts[-1])}.self')
        for e in reversed(elts):
            result = LeanApp(func=LeanApp(func=LeanIdent('List.cons'), arg=e), arg=result)
        return result
    elif isinstance(node, PyTuple):
        elts = [_expr_to_lean(e) for e in node.elts]
        if not elts:
            return LeanUnit()
        result = elts[0]
        for e in elts[1:]:
            result = LeanApp(func=LeanApp(func=LeanIdent('Prod.mk'), arg=result), arg=e)
        return result
    elif isinstance(node, PyDict):
        keys = [_expr_to_lean(k) for k in node.keys if k]
        values = [_expr_to_lean(v) for v in node.values]
        result = LeanIdent('HashMap.empty')
        for k, v in zip(reversed(keys), reversed(values)):
            result = LeanApp(func=LeanApp(func=LeanApp(func=LeanIdent('HashMap.insert'),
                                                      arg=result), arg=k), arg=v)
        return result
    elif isinstance(node, PyLambda):
        args = [(arg_name, _py_type_to_lean_type(ann) if ann else None)
                for arg_name, ann in node.args]
        params = [LeanParam(name=_escape_name(n), type=t) for n, t in args]
        body = _expr_to_lean(node.body)
        return LeanLambda(params=params, body=body)
    elif isinstance(node, PyStarred):
        return _expr_to_lean(node.value)
    elif isinstance(node, PyWalrus):
        return _expr_to_lean(node.value)
    return LeanHole()


def _py_type_to_lean_type(node: PyExpr) -> LeanExpr:
    if isinstance(node, PyName):
        name = node.id
        if name == 'None':
            return LeanIdent('Unit')
        elif name == 'int':
            return LeanIdent('Int')
        elif name == 'float':
            return LeanIdent('Float')
        elif name == 'bool':
            return LeanIdent('Bool')
        elif name == 'str':
            return LeanIdent('String')
        elif name == 'bytes':
            return LeanIdent('ByteArray')
        elif name == 'list':
            return LeanApp(func=LeanIdent('List'), arg=LeanHole())
        elif name == 'dict':
            return LeanApp(func=LeanApp(func=LeanIdent('HashMap'), arg=LeanHole()), arg=LeanHole())
        elif name == 'set':
            return LeanApp(func=LeanIdent('Set'), arg=LeanHole())
        elif name == 'tuple':
            return LeanIdent('Prod')
        elif name == 'Any':
            return LeanSort()
        return LeanIdent(name)
    elif isinstance(node, PySubscript):
        value = _py_type_to_lean_type(node.value) if not isinstance(node.value, PyName) else \
                _py_type_to_lean_type(node.value)
        slice_val = _expr_to_lean(node.slice)
        if isinstance(node.value, PyName):
            base = node.value.id
            if base in ('list', 'List'):
                return LeanApp(func=LeanIdent('List'), arg=slice_val)
            elif base in ('dict', 'Dict'):
                return LeanApp(func=LeanApp(func=LeanIdent('HashMap'), arg=LeanHole()), arg=slice_val)
            elif base in ('tuple', 'Tuple'):
                return LeanApp(func=LeanIdent('Prod'), arg=slice_val)
            elif base in ('optional', 'Optional'):
                return LeanApp(func=LeanIdent('Option'), arg=slice_val)
            elif base in ('set', 'Set'):
                return LeanApp(func=LeanIdent('Set'), arg=slice_val)
            return LeanApp(func=LeanIdent(base), arg=slice_val)
        return LeanApp(func=value, arg=slice_val)
    elif isinstance(node, PyAttribute):
        return LeanProj(expr=_py_type_to_lean_type(node.value), field=node.attr)
    elif isinstance(node, PyConstant):
        if isinstance(node.value, str):
            return LeanIdent(node.value)
    return LeanHole()


def _py_pat_to_lean(node: PyExpr) -> LeanPattern:
    if isinstance(node, PyName):
        if node.id == '_':
            return LeanPatternWild()
        return LeanPatternIdent(name=_escape_name(node.id))
    elif isinstance(node, PyConstant):
        if isinstance(node.value, int):
            return LeanPatternNum(value=node.value)
        elif isinstance(node.value, bool):
            return LeanPatternCtor(name='true' if node.value else 'false', patterns=[])
        elif node.value is None:
            return LeanPatternCtor(name='none', patterns=[])
        return LeanPatternIdent(name=repr(node.value))
    return LeanPatternWild()


def _assign_target_name(node: PyExpr) -> str:
    if isinstance(node, PyName):
        return node.id
    return '_'


def _call_to_lean_print(node: PyCall) -> LeanExpr:
    if node.args:
        return LeanApp(func=LeanIdent('IO.println'), arg=_expr_to_lean(node.args[0]))
    return LeanIdent('IO.println')
