from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LeanNode:
    pass


@dataclass
class LeanModule(LeanNode):
    imports: list[str]
    body: list[LeanNode]


@dataclass
class LeanCommand(LeanNode):
    pass


@dataclass
class LeanExpr(LeanNode):
    pass


@dataclass
class LeanPattern(LeanNode):
    pass


@dataclass
class LeanTactic(LeanNode):
    pass


@dataclass
class LeanDef(LeanCommand):
    name: str
    params: list[LeanParam]
    return_type: Optional[LeanExpr]
    value: Optional[LeanExpr]
    is_theorem: bool = False
    is_lemma: bool = False
    is_mutual: bool = False
    sig_only: bool = False


@dataclass
class LeanParam(LeanNode):
    name: str
    type: Optional[LeanExpr]
    default: Optional[LeanExpr] = None
    explicit: bool = True


@dataclass
class LeanAxiom(LeanCommand):
    name: str
    params: list[LeanParam]
    type: LeanExpr


@dataclass
class LeanInductive(LeanCommand):
    name: str
    params: list[LeanParam]
    type: LeanExpr
    constructors: list[LeanConstructor]


@dataclass
class LeanConstructor(LeanNode):
    name: str
    fields: list[LeanParam]


@dataclass
class LeanStructure(LeanCommand):
    name: str
    params: list[LeanParam]
    extends: list[LeanExpr]
    fields: list[LeanParam]


@dataclass
class LeanClass(LeanCommand):
    name: str
    params: list[LeanParam]
    extends: list[LeanExpr]
    fields: list[LeanParam]


@dataclass
class LeanInstance(LeanCommand):
    name: str
    params: list[LeanParam]
    type: LeanExpr
    methods: list[LeanDef]


@dataclass
class LeanExample(LeanCommand):
    expr: LeanExpr


@dataclass
class LeanOpen(LeanCommand):
    names: list[str]


@dataclass
class LeanNamespace(LeanCommand):
    name: str
    commands: list[LeanCommand]


@dataclass
class LeanSection(LeanCommand):
    params: list[LeanParam]
    commands: list[LeanCommand]


@dataclass
class LeanVariable(LeanCommand):
    params: list[LeanParam]


@dataclass
class LeanLet(LeanExpr):
    name: str
    params: list[LeanParam]
    type: Optional[LeanExpr]
    value: Optional[LeanExpr]
    body: LeanExpr
    is_mut: bool = False


@dataclass
class LeanHave(LeanExpr):
    name: Optional[str]
    type: LeanExpr
    value: LeanExpr
    body: LeanExpr


@dataclass
class LeanShow(LeanExpr):
    type: LeanExpr
    value: LeanExpr


@dataclass
class LeanCalc(LeanExpr):
    steps: list[LeanCalcStep]


@dataclass
class LeanCalcStep(LeanNode):
    relation: LeanExpr
    value: LeanExpr


@dataclass
class LeanLambda(LeanExpr):
    params: list[LeanParam]
    body: LeanExpr


@dataclass
class LeanForall(LeanExpr):
    params: list[LeanParam]
    body: LeanExpr


@dataclass
class LeanPi(LeanExpr):
    binder: LeanParam
    body: LeanExpr


@dataclass
class LeanSort(LeanExpr):
    level: Optional[int] = None


@dataclass
class LeanApp(LeanExpr):
    func: LeanExpr
    arg: LeanExpr


@dataclass
class LeanBinOp(LeanExpr):
    left: LeanExpr
    op: str
    right: LeanExpr


@dataclass
class LeanUnaryOp(LeanExpr):
    op: str
    operand: LeanExpr


@dataclass
class LeanIdent(LeanExpr):
    name: str


@dataclass
class LeanNum(LeanExpr):
    value: int
    is_nat: bool = True


@dataclass
class LeanFloat(LeanExpr):
    value: float


@dataclass
class LeanString(LeanExpr):
    value: str


@dataclass
class LeanChar(LeanExpr):
    value: str


@dataclass
class LeanBool(LeanExpr):
    value: bool


@dataclass
class LeanUnit(LeanExpr):
    pass


@dataclass
class LeanListLit(LeanExpr):
    elts: list[LeanExpr]
    type: Optional[LeanExpr] = None


@dataclass
class LeanTupleLit(LeanExpr):
    elts: list[LeanExpr]


@dataclass
class LeanStructInst(LeanExpr):
    struct_name: str
    fields: list[tuple[str, LeanExpr]]


@dataclass
class LeanProj(LeanExpr):
    expr: LeanExpr
    field: str


@dataclass
class LeanMatch(LeanExpr):
    expr: LeanExpr
    arms: list[LeanMatchArm]


@dataclass
class LeanMatchArm(LeanNode):
    pattern: LeanPattern
    rhs: LeanExpr


@dataclass
class LeanPatternIdent(LeanPattern):
    name: str


@dataclass
class LeanPatternWild(LeanPattern):
    pass


@dataclass
class LeanPatternOr(LeanPattern):
    patterns: list[LeanPattern]


@dataclass
class LeanPatternCtor(LeanPattern):
    name: str
    patterns: list[LeanPattern]


@dataclass
class LeanPatternNum(LeanPattern):
    value: int


@dataclass
class LeanPatternStruct(LeanPattern):
    name: str
    fields: list[tuple[str, LeanPattern]]


@dataclass
class LeanIf(LeanExpr):
    cond: LeanExpr
    then_expr: LeanExpr
    else_expr: Optional[LeanExpr]


@dataclass
class LeanTypeSpec(LeanExpr):
    expr: LeanExpr
    type: LeanExpr


@dataclass
class LeanHaveStmt(LeanCommand):
    name: Optional[str]
    type: LeanExpr
    value: LeanExpr


@dataclass
class LeanDo(LeanExpr):
    stmts: list[LeanDoStmt]
    last: Optional[LeanExpr]


@dataclass
class LeanDoStmt(LeanNode):
    pass


@dataclass
class LeanDoLet(LeanDoStmt):
    name: str
    value: LeanExpr
    is_mut: bool = False


@dataclass
class LeanDoBind(LeanDoStmt):
    pattern: LeanPattern
    value: LeanExpr


@dataclass
class LeanDoExpr(LeanDoStmt):
    expr: LeanExpr


@dataclass
class LeanHole(LeanExpr):
    pass


@dataclass
class LeanParenthesized(LeanExpr):
    expr: LeanExpr


@dataclass
class LeanBy(LeanExpr):
    tactic: LeanTactic


@dataclass
class LeanNamedArg(LeanExpr):
    name: str
    value: LeanExpr


@dataclass
class LeanTypeArrow(LeanExpr):
    from_type: LeanExpr
    to_type: LeanExpr


@dataclass
class LeanPlaceholder(LeanExpr):
    pass
