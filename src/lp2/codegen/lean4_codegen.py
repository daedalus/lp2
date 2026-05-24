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


# ---------------------------------------------------------------------------
# Command dispatch
# ---------------------------------------------------------------------------


def _gen_cmd_Def(node: LeanDef, indent: int) -> str:
    return _gen_def(node)


def _gen_cmd_Open(node: LeanOpen, indent: int) -> str:
    return f"open {' '.join(node.names)}"


def _gen_cmd_Inductive(node: LeanInductive, indent: int) -> str:
    return _gen_inductive(node)


def _gen_cmd_Structure(node: LeanStructure, indent: int) -> str:
    return _gen_structure(node)


def _gen_cmd_Class(node: LeanClass, indent: int) -> str:
    return _gen_class(node)


def _gen_cmd_Instance(node: LeanInstance, indent: int) -> str:
    return _gen_instance(node)


def _gen_cmd_Axiom(node: LeanAxiom, indent: int) -> str:
    params = _gen_params(node.params)
    return f"axiom {node.name}{params} : {_gen_expr(node.type)}"


def _gen_cmd_Example(node: LeanExample, indent: int) -> str:
    return f"#eval {_gen_expr(node.expr)}"


def _gen_cmd_Variable(node: LeanVariable, indent: int) -> str:
    return f"variable {' '.join(_gen_param(p) for p in node.params)}"


def _gen_cmd_Namespace(node: LeanNamespace, indent: int) -> str:
    body = "\n".join(_gen_command(c, indent + 1) for c in node.commands)
    return f"namespace {node.name}\n{body}\nend {node.name}"


def _gen_cmd_Section(node: LeanSection, indent: int) -> str:
    body = "\n".join(_gen_command(c, indent + 1) for c in node.commands)
    params = (
        (" " + " ".join(_gen_param(p) for p in node.params)) if node.params else ""
    )
    return f"section{params}\n{body}\nend"


_CMD_GEN = {
    LeanDef: _gen_cmd_Def,
    LeanOpen: _gen_cmd_Open,
    LeanInductive: _gen_cmd_Inductive,
    LeanStructure: _gen_cmd_Structure,
    LeanClass: _gen_cmd_Class,
    LeanInstance: _gen_cmd_Instance,
    LeanAxiom: _gen_cmd_Axiom,
    LeanExample: _gen_cmd_Example,
    LeanVariable: _gen_cmd_Variable,
    LeanNamespace: _gen_cmd_Namespace,
    LeanSection: _gen_cmd_Section,
}


def _gen_command(node: LeanCommand, indent: int) -> str:
    handler = _CMD_GEN.get(type(node))
    if handler is not None:
        return handler(node, indent)
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
    return " (" + ") (".join(parts) + ")"


def _gen_param(p: LeanParam) -> str:
    if p.type:
        return f"{p.name} : {_gen_expr(p.type)}"
    return p.name


# ---------------------------------------------------------------------------
# Expression dispatch
# ---------------------------------------------------------------------------


def _needs_parens(n: LeanExpr) -> bool:
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


def _gen_expr_Ident(node: LeanExpr, parent_prec: int = 0) -> str:
    return node.name


def _gen_expr_Num(node: LeanExpr, parent_prec: int = 0) -> str:
    return str(node.value)


def _gen_expr_Float(node: LeanExpr, parent_prec: int = 0) -> str:
    return str(node.value)


def _gen_expr_String(node: LeanExpr, parent_prec: int = 0) -> str:
    s = node.value
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    s = s.replace("\n", "\\n")
    s = s.replace("\t", "\\t")
    s = s.replace("\r", "\\r")
    return f'"{s}"'


def _gen_expr_Char(node: LeanExpr, parent_prec: int = 0) -> str:
    return repr(node.value)


def _gen_expr_Bool(node: LeanExpr, parent_prec: int = 0) -> str:
    return "true" if node.value else "false"


def _gen_expr_Unit(node: LeanExpr, parent_prec: int = 0) -> str:
    return "()"


def _gen_expr_Hole(node: LeanExpr, parent_prec: int = 0) -> str:
    return "_"


def _gen_expr_Sort(node: LeanExpr, parent_prec: int = 0) -> str:
    if node.level is not None:
        return f"Type {node.level}"
    return "Type"


def _gen_expr_App(node: LeanExpr, parent_prec: int = 0) -> str:
    func_str = _gen_expr(node.func)
    arg_str = _gen_expr(node.arg)
    if _needs_parens(node.arg):
        arg_str = f"({arg_str})"
    if _needs_parens(node.func):
        func_str = f"({func_str})"
    return f"{func_str} {arg_str}"


_BINOP_PREC: dict[str, int] = {
    "||": 1,
    "&&": 2,
    "==": 3, "!=": 3, "<": 3, ">": 3, "<=": 3, ">=": 3,
    "+": 5, "-": 5,
    "*": 6, "/": 6, "%": 6,
    "^": 7,
}


def _binop_prec(op: str) -> int:
    return _BINOP_PREC.get(op, 4)


def _gen_binop_operand(node: LeanExpr, parent_op: str, is_right: bool) -> str:
    """Wrap ``node`` in parens when needed to preserve operator precedence."""
    if isinstance(node, LeanBinOp):
        child_prec = _binop_prec(node.op)
        parent_prec = _binop_prec(parent_op)
        if child_prec < parent_prec or (is_right and child_prec == parent_prec):
            return f"({_gen_expr_BinOp(node)})"
    return _gen_expr(node)


def _gen_expr_BinOp(node: LeanExpr, parent_prec: int = 0) -> str:
    left = _gen_binop_operand(node.left, node.op, is_right=False)
    right = _gen_binop_operand(node.right, node.op, is_right=True)
    return f"{left} {node.op} {right}"


def _gen_expr_UnaryOp(node: LeanExpr, parent_prec: int = 0) -> str:
    operand = _gen_expr(node.operand)
    sep = " " if node.op.isalpha() else ""
    return f"{node.op}{sep}{operand}"


def _gen_expr_TypeArrow(node: LeanExpr, parent_prec: int = 0) -> str:
    return f"({_gen_expr(node.from_type)} → {_gen_expr(node.to_type)})"


def _gen_expr_TypeSpec(node: LeanExpr, parent_prec: int = 0) -> str:
    return f"({_gen_expr(node.expr)} : {_gen_expr(node.type)})"


def _gen_expr_Lambda(node: LeanExpr, parent_prec: int = 0) -> str:
    params = " ".join(_gen_param(p) for p in node.params)
    return f"fun {params} => {_gen_expr(node.body)}"


def _gen_expr_Forall(node: LeanExpr, parent_prec: int = 0) -> str:
    params = " ".join(
        f"({p.name} : {_gen_expr(p.type)})" if p.type else p.name
        for p in node.params
    )
    return f"∀ {params}, {_gen_expr(node.body)}"


def _gen_expr_Pi(node: LeanExpr, parent_prec: int = 0) -> str:
    binder = _gen_param(node.binder)
    return f"({binder}) → {_gen_expr(node.body)}"


def _gen_expr_ListLit(node: LeanExpr, parent_prec: int = 0) -> str:
    return f"[{', '.join(_gen_expr(e) for e in node.elts)}]"


def _gen_expr_TupleLit(node: LeanExpr, parent_prec: int = 0) -> str:
    return f"({', '.join(_gen_expr(e) for e in node.elts)})"


def _gen_expr_StructInst(node: LeanExpr, parent_prec: int = 0) -> str:
    fields = ", ".join(f"{n} := {_gen_expr(v)}" for n, v in node.fields)
    return (
        f"{{ {node.struct_name} with {fields} }}"
        if node.fields
        else f"{{ {node.struct_name} }}"
    )


def _gen_expr_Proj(node: LeanExpr, parent_prec: int = 0) -> str:
    return f"{_gen_expr(node.expr)}.{node.field}"


def _gen_expr_Match(node: LeanExpr, parent_prec: int = 0) -> str:
    arms = "\n    ".join(
        f"| {_gen_pattern(arm.pattern)} => {_gen_expr(arm.rhs)}"
        for arm in node.arms
    )
    return f"match {_gen_expr(node.expr)} with\n    {arms}"


def _gen_expr_If(node: LeanExpr, parent_prec: int = 0) -> str:
    result = f"if {_gen_expr(node.cond)} then {_gen_expr(node.then_expr)}"
    if node.else_expr:
        result += f" else {_gen_expr(node.else_expr)}"
    return result


def _gen_expr_Let(node: LeanExpr, parent_prec: int = 0) -> str:
    params = _gen_params(node.params)
    typ = f" : {_gen_expr(node.type)}" if node.type else ""
    val = _gen_expr(node.value)
    return f"let {node.name}{params}{typ} := {val}; {_gen_expr(node.body)}"


def _gen_expr_Have(node: LeanExpr, parent_prec: int = 0) -> str:
    name = f" {node.name} :" if node.name else " "
    return f"have{name}{_gen_expr(node.type)} := {_gen_expr(node.value)}; {_gen_expr(node.body)}"


def _gen_expr_Show(node: LeanExpr, parent_prec: int = 0) -> str:
    return f"show {_gen_expr(node.type)} from {_gen_expr(node.value)}"


def _gen_expr_Calc(node: LeanExpr, parent_prec: int = 0) -> str:
    steps = "\n    ".join(
        f"{_gen_expr(s.relation)} := {_gen_expr(s.value)}" for s in node.steps
    )
    return f"calc\n    {steps}"


def _gen_expr_Do(node: LeanExpr, parent_prec: int = 0) -> str:
    stmts_str = ";\n    ".join(_gen_do_stmt(s) for s in node.stmts)
    last_str = _gen_expr(node.last) if node.last else ""
    if stmts_str and last_str:
        return f"do\n    {stmts_str};\n    {last_str}"
    elif stmts_str:
        return f"do\n    {stmts_str}"
    elif last_str:
        return f"do\n    {last_str}"
    return "do"


def _gen_expr_By(node: LeanExpr, parent_prec: int = 0) -> str:
    return f"by {_gen_expr(node.tactic)}"


def _gen_expr_Parenthesized(node: LeanExpr, parent_prec: int = 0) -> str:
    return f"({_gen_expr(node.expr)})"


def _gen_expr_NamedArg(node: LeanExpr, parent_prec: int = 0) -> str:
    return f"{node.name} := {_gen_expr(node.value)}"


_EXPR_GEN_LEAN = {
    LeanIdent: _gen_expr_Ident,
    LeanNum: _gen_expr_Num,
    LeanFloat: _gen_expr_Float,
    LeanString: _gen_expr_String,
    LeanChar: _gen_expr_Char,
    LeanBool: _gen_expr_Bool,
    LeanUnit: _gen_expr_Unit,
    LeanHole: _gen_expr_Hole,
    LeanSort: _gen_expr_Sort,
    LeanApp: _gen_expr_App,
    LeanBinOp: _gen_expr_BinOp,
    LeanUnaryOp: _gen_expr_UnaryOp,
    LeanTypeArrow: _gen_expr_TypeArrow,
    LeanTypeSpec: _gen_expr_TypeSpec,
    LeanLambda: _gen_expr_Lambda,
    LeanForall: _gen_expr_Forall,
    LeanPi: _gen_expr_Pi,
    LeanListLit: _gen_expr_ListLit,
    LeanTupleLit: _gen_expr_TupleLit,
    LeanStructInst: _gen_expr_StructInst,
    LeanProj: _gen_expr_Proj,
    LeanMatch: _gen_expr_Match,
    LeanIf: _gen_expr_If,
    LeanLet: _gen_expr_Let,
    LeanHave: _gen_expr_Have,
    LeanShow: _gen_expr_Show,
    LeanCalc: _gen_expr_Calc,
    LeanDo: _gen_expr_Do,
    LeanBy: _gen_expr_By,
    LeanParenthesized: _gen_expr_Parenthesized,
    LeanNamedArg: _gen_expr_NamedArg,
}


def _gen_expr(node: LeanExpr, parent_prec: int = 0) -> str:
    if node is None:
        return "_"
    handler = _EXPR_GEN_LEAN.get(type(node))
    if handler is not None:
        return handler(node, parent_prec)
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
