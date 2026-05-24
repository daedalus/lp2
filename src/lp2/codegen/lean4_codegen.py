from lp2.ast.lean4_ast import *


def generate_lean(node: LeanNode) -> str:
    if isinstance(node, LeanModule):
        return _gen_module(node)
    raise ValueError(f"Unknown node: {type(node).__name__}")


def _gen_module(node: LeanModule) -> str:
    lines = []
    if node.imports:
        for imp in node.imports:
            lines.append(f"import {imp}")
    for cmd in node.body:
        lines.append(_gen_command(cmd, 0))
        lines.append("")
    return "\n".join(lines)


def _gen_command(node: LeanCommand, indent: int) -> str:
    i = "  " * indent
    if isinstance(node, LeanDef):
        return _gen_def(node)
    elif isinstance(node, LeanOpen):
        return f"open {' '.join(node.names)}"
    elif isinstance(node, LeanInductive):
        return _gen_inductive(node)
    elif isinstance(node, LeanStructure):
        return _gen_structure(node)
    elif isinstance(node, LeanClass):
        return _gen_class(node)
    elif isinstance(node, LeanInstance):
        return _gen_instance(node)
    elif isinstance(node, LeanAxiom):
        kw = "axiom"
        params = _gen_params(node.params)
        return f"{kw} {node.name}{params} : {_gen_expr(node.type)}"
    elif isinstance(node, LeanExample):
        return f"#eval {_gen_expr(node.expr)}"
    elif isinstance(node, LeanVariable):
        return f"variable {' '.join(_gen_param(p) for p in node.params)}"
    elif isinstance(node, LeanNamespace):
        body = "\n".join(_gen_command(c, indent + 1) for c in node.commands)
        return f"namespace {node.name}\n{body}\nend {node.name}"
    elif isinstance(node, LeanSection):
        body = "\n".join(_gen_command(c, indent + 1) for c in node.commands)
        params = (
            (" " + " ".join(_gen_param(p) for p in node.params)) if node.params else ""
        )
        return f"section{params}\n{body}\nend"
    raise ValueError(f"Unknown command: {type(node).__name__}")


def _gen_def(node: LeanDef) -> str:
    if node.is_theorem:
        kw = "theorem"
    elif node.is_lemma:
        kw = "lemma"
    else:
        kw = "def"
    params = _gen_params(node.params)
    ret = ""
    if node.return_type:
        ret = f" : {_gen_expr(node.return_type)}"
    if node.sig_only:
        return f"{kw} {node.name}{params}{ret}"
    if node.value is None:
        return f"{kw} {node.name}{params}{ret}"
    val = _gen_expr(node.value)
    return f"{kw} {node.name}{params}{ret} :=\n  {val}"


def _gen_inductive(node: LeanInductive) -> str:
    params = _gen_params(node.params)
    typ = _gen_expr(node.type) if not isinstance(node.type, LeanSort) else "Type"
    lines = [f"inductive {node.name}{params} : {typ} where"]
    for ctor in node.constructors:
        fields = "".join(f" ({_gen_expr(f.type)})" for f in ctor.fields if f.type)
        lines.append(f"  | {ctor.name}{fields}")
    return "\n".join(lines)


def _gen_structure(node: LeanStructure) -> str:
    params = _gen_params(node.params)
    lines = [f"structure {node.name}{params} where"]
    for field in node.fields:
        lines.append(f"  {field.name} : {_gen_expr(field.type)}")
    return "\n".join(lines)


def _gen_class(node: LeanClass) -> str:
    params = _gen_params(node.params)
    lines = [f"class {node.name}{params} where"]
    for field in node.fields:
        lines.append(f"  {field.name} : {_gen_expr(field.type)}")
    return "\n".join(lines)


def _gen_instance(node: LeanInstance) -> str:
    params = _gen_params(node.params)
    lines = [f"instance {node.name}{params} : {_gen_expr(node.type)} where"]
    for method in node.methods:
        lines.append(f"  {_gen_def(method)}")
    return "\n".join(lines)


def _gen_params(params: list[LeanParam]) -> str:
    if not params:
        return ""
    parts = []
    for p in params:
        parts.append(_gen_param(p))
    if len(parts) <= 2:
        return " (" + ") (".join(parts) + ")"
    return " (" + ") (".join(parts) + ")"


def _gen_param(p: LeanParam) -> str:
    if p.type:
        return f"{p.name} : {_gen_expr(p.type)}"
    return p.name


def _gen_expr(node: LeanExpr) -> str:
    if node is None:
        return "_"
    if isinstance(node, LeanIdent):
        return node.name
    elif isinstance(node, LeanNum):
        return str(node.value)
    elif isinstance(node, LeanFloat):
        return str(node.value)
    elif isinstance(node, LeanString):
        return repr(node.value)
    elif isinstance(node, LeanChar):
        return repr(node.value)
    elif isinstance(node, LeanBool):
        return "true" if node.value else "false"
    elif isinstance(node, LeanUnit):
        return "()"
    elif isinstance(node, LeanHole):
        return "_"
    elif isinstance(node, LeanSort):
        if node.level is not None:
            return f"Type {node.level}"
        return "Type"
    elif isinstance(node, LeanApp):

        def needs_parens(n: LeanExpr) -> bool:
            return isinstance(
                n,
                (
                    LeanApp,
                    LeanBinOp,
                    LeanUnaryOp,
                    LeanLambda,
                    LeanIf,
                    LeanMatch,
                    LeanLet,
                    LeanTypeArrow,
                    LeanTypeSpec,
                ),
            )

        func_str = _gen_expr(node.func)
        arg_str = _gen_expr(node.arg)
        if needs_parens(node.arg):
            arg_str = f"({arg_str})"
        if needs_parens(node.func):
            func_str = f"({func_str})"
        return f"{func_str} {arg_str}"
    elif isinstance(node, LeanBinOp):
        return f"{_gen_expr(node.left)} {node.op} {_gen_expr(node.right)}"
    elif isinstance(node, LeanUnaryOp):
        return f"{node.op}{_gen_expr(node.operand)}"
    elif isinstance(node, LeanTypeArrow):
        return f"({_gen_expr(node.from_type)} → {_gen_expr(node.to_type)})"
    elif isinstance(node, LeanTypeSpec):
        return f"({_gen_expr(node.expr)} : {_gen_expr(node.type)})"
    elif isinstance(node, LeanLambda):
        params = " ".join(_gen_param(p) for p in node.params)
        return f"fun {params} => {_gen_expr(node.body)}"
    elif isinstance(node, LeanForall):
        params = " ".join(
            f"({p.name} : {_gen_expr(p.type)})" if p.type else p.name
            for p in node.params
        )
        return f"∀ {params}, {_gen_expr(node.body)}"
    elif isinstance(node, LeanPi):
        binder = _gen_param(node.binder)
        return f"({binder}) → {_gen_expr(node.body)}"
    elif isinstance(node, LeanListLit):
        return f"[{', '.join(_gen_expr(e) for e in node.elts)}]"
    elif isinstance(node, LeanTupleLit):
        return f"({', '.join(_gen_expr(e) for e in node.elts)})"
    elif isinstance(node, LeanStructInst):
        fields = ", ".join(f"{n} := {_gen_expr(v)}" for n, v in node.fields)
        return (
            f"{{ {node.struct_name} with {fields} }}"
            if node.fields
            else f"{{ {node.struct_name} }}"
        )
    elif isinstance(node, LeanProj):
        return f"{_gen_expr(node.expr)}.{node.field}"
    elif isinstance(node, LeanMatch):
        arms = "\n    ".join(
            f"| {_gen_pattern(arm.pattern)} => {_gen_expr(arm.rhs)}"
            for arm in node.arms
        )
        return f"match {_gen_expr(node.expr)} with\n    {arms}"
    elif isinstance(node, LeanIf):
        result = f"if {_gen_expr(node.cond)} then {_gen_expr(node.then_expr)}"
        if node.else_expr:
            result += f" else {_gen_expr(node.else_expr)}"
        return result
    elif isinstance(node, LeanLet):
        params = _gen_params(node.params)
        typ = f" : {_gen_expr(node.type)}" if node.type else ""
        val = _gen_expr(node.value)
        return f"let {node.name}{params}{typ} := {val} in {_gen_expr(node.body)}"
    elif isinstance(node, LeanHave):
        name = f" {node.name} :" if node.name else " "
        return f"have{name}{_gen_expr(node.type)} := {_gen_expr(node.value)}; {_gen_expr(node.body)}"
    elif isinstance(node, LeanShow):
        return f"show {_gen_expr(node.type)} from {_gen_expr(node.value)}"
    elif isinstance(node, LeanCalc):
        steps = "\n    ".join(
            f"{_gen_expr(s.relation)} := {_gen_expr(s.value)}" for s in node.steps
        )
        return f"calc\n    {steps}"
    elif isinstance(node, LeanDo):
        stmts_str = ";\n    ".join(_gen_do_stmt(s) for s in node.stmts)
        last_str = _gen_expr(node.last) if node.last else ""
        if stmts_str and last_str:
            return f"do\n    {stmts_str};\n    {last_str}"
        elif stmts_str:
            return f"do\n    {stmts_str}"
        elif last_str:
            return f"do\n    {last_str}"
        return "do"
    elif isinstance(node, LeanBy):
        return f"by {_gen_expr(node.tactic)}"
    elif isinstance(node, LeanParenthesized):
        return f"({_gen_expr(node.expr)})"
    elif isinstance(node, LeanNamedArg):
        return f"{node.name} := {_gen_expr(node.value)}"
    raise ValueError(f"Unknown expression: {type(node).__name__}")


def _gen_do_stmt(node: LeanDoStmt) -> str:
    if isinstance(node, LeanDoLet):
        return f"let {node.name} := {_gen_expr(node.value)}"
    elif isinstance(node, LeanDoBind):
        return f"{_gen_pattern(node.pattern)} <- {_gen_expr(node.value)}"
    elif isinstance(node, LeanDoExpr):
        return _gen_expr(node.expr)
    return ""


def _gen_pattern(node: LeanPattern) -> str:
    if isinstance(node, LeanPatternIdent):
        return node.name
    elif isinstance(node, LeanPatternWild):
        return "_"
    elif isinstance(node, LeanPatternNum):
        return str(node.value)
    elif isinstance(node, LeanPatternOr):
        return " | ".join(_gen_pattern(p) for p in node.patterns)
    elif isinstance(node, LeanPatternCtor):
        if node.patterns:
            return f"{node.name} {' '.join(_gen_pattern(p) for p in node.patterns)}"
        return node.name
    elif isinstance(node, LeanPatternStruct):
        fields = ", ".join(f"{n} := {_gen_pattern(p)}" for n, p in node.fields)
        return f"{node.name} {{ {fields} }}"
    raise ValueError(f"Unknown pattern: {type(node).__name__}")
