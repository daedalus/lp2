from lp2.ast.python_ast import *


def generate_python(node: PyNode) -> str:
    if isinstance(node, PyModule):
        return _gen_module(node)
    raise ValueError(f"Unknown node: {type(node).__name__}")


def _gen_module(node: PyModule) -> str:
    lines = []
    for stmt in node.body:
        lines.append(_gen_stmt(stmt, 0))
    return '\n'.join(lines) + '\n'


def _gen_stmt(node: PyStmt, indent: int) -> str:
    i = '    ' * indent
    if isinstance(node, PyFunctionDef):
        parts = [f'{i}def {node.name}(']
        arg_parts = []
        for arg_name, annotation, default in node.args:
            a = arg_name
            if annotation:
                a += f': {_gen_expr(annotation)}'
            if default is not None:
                a += f' = {_gen_expr(default)}'
            arg_parts.append(a)
        parts.append(', '.join(arg_parts))
        parts.append(')')
        if node.return_type:
            parts.append(f' -> {_gen_expr(node.return_type)}')
        parts.append(':')
        lines = [''.join(parts)]
        if not node.body:
            lines.append(f'{i}    pass')
        else:
            for s in node.body:
                lines.append(_gen_stmt(s, indent + 1))
        return '\n'.join(lines)
    elif isinstance(node, PyClassDef):
        parts = [f'{i}class {node.name}']
        if node.bases:
            parts.append(f'({", ".join(_gen_expr(b) for b in node.bases)})')
        parts.append(':')
        lines = [''.join(parts)]
        if not node.body:
            lines.append(f'{i}    pass')
        else:
            for s in node.body:
                lines.append(_gen_stmt(s, indent + 1))
        return '\n'.join(lines)
    elif isinstance(node, PyReturn):
        if node.value:
            return f'{i}return {_gen_expr(node.value)}'
        return f'{i}return'
    elif isinstance(node, PyAssign):
        return f'{i}{_gen_expr(node.target)} = {_gen_expr(node.value)}'
    elif isinstance(node, PyAnnAssign):
        if node.value:
            return f'{i}{_gen_expr(node.target)}: {_gen_expr(node.annotation)} = {_gen_expr(node.value)}'
        return f'{i}{_gen_expr(node.target)}: {_gen_expr(node.annotation)}'
    elif isinstance(node, PyIf):
        lines = [f'{i}if {_gen_expr(node.test)}:']
        if not node.body:
            lines.append(f'{i}    pass')
        else:
            for s in node.body:
                lines.append(_gen_stmt(s, indent + 1))
        if node.orelse:
            if len(node.orelse) == 1 and isinstance(node.orelse[0], PyIf):
                lines.append(f'{i}elif {_gen_expr(node.orelse[0].test)}:')
                for s in node.orelse[0].body:
                    lines.append(_gen_stmt(s, indent + 1))
                if node.orelse[0].orelse:
                    _append_else(lines, node.orelse[0].orelse, indent, i)
            else:
                lines.append(f'{i}else:')
                for s in node.orelse:
                    lines.append(_gen_stmt(s, indent + 1))
        return '\n'.join(lines)
    elif isinstance(node, PyFor):
        lines = [f'{i}for {_gen_expr(node.target)} in {_gen_expr(node.iter)}:']
        if not node.body:
            lines.append(f'{i}    pass')
        else:
            for s in node.body:
                lines.append(_gen_stmt(s, indent + 1))
        return '\n'.join(lines)
    elif isinstance(node, PyWhile):
        lines = [f'{i}while {_gen_expr(node.test)}:']
        if not node.body:
            lines.append(f'{i}    pass')
        else:
            for s in node.body:
                lines.append(_gen_stmt(s, indent + 1))
        return '\n'.join(lines)
    elif isinstance(node, PyExprStmt):
        return f'{i}{_gen_expr(node.expr)}'
    elif isinstance(node, PyPass):
        return f'{i}pass'
    elif isinstance(node, PyBreak):
        return f'{i}break'
    elif isinstance(node, PyContinue):
        return f'{i}continue'
    elif isinstance(node, PyImport):
        return f'{i}import {", ".join(node.names)}'
    elif isinstance(node, PyRaise):
        return f'{i}raise {_gen_expr(node.exc)}'
    elif isinstance(node, PyTry):
        lines = [f'{i}try:']
        for s in node.body:
            lines.append(_gen_stmt(s, indent + 1))
        for handler in node.handlers:
            lines.append(_gen_except_handler(handler, indent, i))
        if node.orelse:
            lines.append(f'{i}else:')
            for s in node.orelse:
                lines.append(_gen_stmt(s, indent + 1))
        if node.finalbody:
            lines.append(f'{i}finally:')
            for s in node.finalbody:
                lines.append(_gen_stmt(s, indent + 1))
        return '\n'.join(lines)
    elif isinstance(node, PyWith):
        items = ', '.join(f'{_gen_expr(item[0])}' + (f' as {_gen_expr(item[1])}' if item[1] else '') for item in node.items)
        lines = [f'{i}with {items}:']
        for s in node.body:
            lines.append(_gen_stmt(s, indent + 1))
        return '\n'.join(lines)
    elif isinstance(node, PyAssert):
        if node.msg:
            return f'{i}assert {_gen_expr(node.test)}, {_gen_expr(node.msg)}'
        return f'{i}assert {_gen_expr(node.test)}'
    elif isinstance(node, PyGlobal):
        return f'{i}global {", ".join(node.names)}'
    elif isinstance(node, PyNonlocal):
        return f'{i}nonlocal {", ".join(node.names)}'
    elif isinstance(node, PyDelete):
        return f'{i}del {", ".join(_gen_expr(t) for t in node.targets)}'
    elif isinstance(node, PyMatch):
        lines = [f'{i}match {_gen_expr(node.subject)}:']
        for case in node.cases:
            lines.append(f'{i}    case {_gen_pattern_py(case.pattern)}:')
            if case.guard:
                lines.append(f'{i}        if {_gen_expr(case.guard)}:')
                for s in case.body:
                    lines.append(_gen_stmt(s, indent + 3))
            elif not case.body:
                lines.append(f'{i}        pass')
            else:
                for s in case.body:
                    lines.append(_gen_stmt(s, indent + 2))
        return '\n'.join(lines)
    elif isinstance(node, PyTypeAlias):
        return f'{i}type {_gen_expr(node.name)} = {_gen_expr(node.value)}'
    raise ValueError(f"Unknown statement: {type(node).__name__}")


def _append_else(lines, orelse, indent, i):
    if len(orelse) == 1 and isinstance(orelse[0], PyIf):
        lines.append(f'{i}elif {_gen_expr(orelse[0].test)}:')
        for s in orelse[0].body:
            lines.append(_gen_stmt(s, indent + 1))
        if orelse[0].orelse:
            _append_else(lines, orelse[0].orelse, indent, i)
    else:
        lines.append(f'{i}else:')
        for s in orelse:
            lines.append(_gen_stmt(s, indent + 1))


def _gen_except_handler(node: PyExceptHandler, indent: int, i: str) -> str:
    parts = [f'{i}except']
    if node.typ:
        parts.append(f' {_gen_expr(node.typ)}')
    if node.name:
        parts.append(f' as {node.name}')
    parts.append(':')
    lines = [''.join(parts)]
    for s in node.body:
        lines.append(_gen_stmt(s, indent + 1))
    return '\n'.join(lines)


def _gen_expr(node: PyExpr) -> str:
    if node is None:
        return 'None'
    if isinstance(node, PyName):
        return node.id
    elif isinstance(node, PyConstant):
        if node.value is None:
            return 'None'
        elif isinstance(node.value, bool):
            return 'True' if node.value else 'False'
        elif isinstance(node.value, str):
            return repr(node.value)
        elif isinstance(node.value, bytes):
            return repr(node.value)
        return str(node.value)
    elif isinstance(node, PyBinOp):
        return f'{_gen_expr(node.left)} {node.op} {_gen_expr(node.right)}'
    elif isinstance(node, PyUnaryOp):
        return f'{node.op}{_gen_expr(node.operand)}'
    elif isinstance(node, PyCompare):
        parts = [_gen_expr(node.left)]
        for i, op in enumerate(node.ops):
            parts.append(f' {op} {_gen_expr(node.comparators[i])}')
        return ''.join(parts)
    elif isinstance(node, PyBoolOp):
        return f'{f" {node.op} ".join(_gen_expr(v) for v in node.values)}'
    elif isinstance(node, PyCall):
        args = [_gen_expr(a) for a in node.args]
        kwargs = [f'{k}={_gen_expr(v)}' for k, v in node.kwargs]
        return f'{_gen_expr(node.func)}({", ".join(args + kwargs)})'
    elif isinstance(node, PyIfExp):
        return f'{_gen_expr(node.body)} if {_gen_expr(node.test)} else {_gen_expr(node.orelse)}'
    elif isinstance(node, PyAttribute):
        return f'{_gen_expr(node.value)}.{node.attr}'
    elif isinstance(node, PySubscript):
        return f'{_gen_expr(node.value)}[{_gen_expr(node.slice)}]'
    elif isinstance(node, PySlice):
        parts = [
            _gen_expr(node.lower) if node.lower else '',
            ':' + (_gen_expr(node.upper) if node.upper else ''),
        ]
        if node.step:
            parts.append(f':{_gen_expr(node.step)}')
        return ''.join(parts)
    elif isinstance(node, PyList):
        return f'[{", ".join(_gen_expr(e) for e in node.elts)}]'
    elif isinstance(node, PyTuple):
        if len(node.elts) == 1:
            return f'({_gen_expr(node.elts[0])},)'
        return f'({", ".join(_gen_expr(e) for e in node.elts)})'
    elif isinstance(node, PySet):
        return f'{{{", ".join(_gen_expr(e) for e in node.elts)}}}'
    elif isinstance(node, PyDict):
        items = []
        for k, v in zip(node.keys, node.values):
            k_str = _gen_expr(k) if k else ''
            items.append(f'{k_str}: {_gen_expr(v)}')
        return f'{{{", ".join(items)}}}'
    elif isinstance(node, PyLambda):
        args = []
        for arg_name, annotation in node.args:
            a = arg_name
            if annotation:
                a += f': {_gen_expr(annotation)}'
            args.append(a)
        return f'lambda {", ".join(args)}: {_gen_expr(node.body)}'
    elif isinstance(node, PyListComp):
        return f'[{_gen_expr(node.elt)} {_gen_comp_generators(node.generators)}]'
    elif isinstance(node, PySetComp):
        return f'{{{_gen_expr(node.elt)} {_gen_comp_generators(node.generators)}}}'
    elif isinstance(node, PyDictComp):
        return f'{{{_gen_expr(node.key)}: {_gen_expr(node.value)} {_gen_comp_generators(node.generators)}}}'
    elif isinstance(node, PyStarred):
        return f'*{_gen_expr(node.value)}'
    elif isinstance(node, PyAwait):
        return f'await {_gen_expr(node.value)}'
    elif isinstance(node, PyYield):
        if node.value:
            return f'yield {_gen_expr(node.value)}'
        return 'yield'
    elif isinstance(node, PyYieldFrom):
        return f'yield from {_gen_expr(node.value)}'
    elif isinstance(node, PyWalrus):
        return f'{_gen_expr(node.target)} := {_gen_expr(node.value)}'
    elif isinstance(node, PyMatch):
        # simplified
        return f'match {_gen_expr(node.subject)}'
    elif isinstance(node, PyMatchCase):
        # simplified
        return f'case {_gen_expr(node.pattern)}'
    elif isinstance(node, PyMatch):
        return f'match {_gen_expr(node.subject)}'
    elif isinstance(node, PyMatchCase):
        return f'case {_gen_pattern_py(node.pattern)}'
    raise ValueError(f"Unknown expression: {type(node).__name__}")


def _gen_pattern_py(node: PyExpr) -> str:
    if isinstance(node, PyName):
        return node.id
    if isinstance(node, PyConstant):
        if isinstance(node.value, bool):
            return 'True' if node.value else 'False'
        if node.value is None:
            return 'None'
        return repr(node.value)
    return _gen_expr(node)


def _gen_comp_generators(generators: list[PyComprehension]) -> str:
    parts = []
    for g in generators:
        async_prefix = 'async ' if g.is_async else ''
        ifs = ''.join(f' if {_gen_expr(if_clause)}' for if_clause in g.ifs)
        parts.append(f'{async_prefix}for {_gen_expr(g.target)} in {_gen_expr(g.iter)}{ifs}')
    return ' '.join(parts)
