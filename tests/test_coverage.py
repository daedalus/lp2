"""Targeted tests to exercise uncovered codegen, transpiler, and parser paths."""

import pytest

from lp2 import lean_to_py, py_to_lean
from lp2.ast.lean4_ast import *
from lp2.ast.python_ast import *
from lp2.codegen.lean4_codegen import generate_lean
from lp2.codegen.python_codegen import generate_python

# ---------------------------------------------------------------------------
# lean4_codegen.py — direct AST construction → generate_lean
# ---------------------------------------------------------------------------


class TestLeanCodegenCommands:
    def test_non_module_raises(self):
        with pytest.raises(ValueError, match="Unknown node"):
            generate_lean(LeanIdent("x"))  # type: ignore

    def test_module_with_imports(self):
        m = LeanModule(imports=["Foo", "Bar"], body=[])
        out = generate_lean(m)
        assert "import Foo" in out
        assert "import Bar" in out

    def test_open(self):
        m = LeanModule(imports=[], body=[LeanOpen(names=["Foo", "Bar"])])
        out = generate_lean(m)
        assert "open Foo Bar" in out

    def test_inductive_with_fields(self):
        m = LeanModule(
            imports=[],
            body=[
                LeanInductive(
                    name="Foo",
                    params=[],
                    type=LeanSort(None),
                    constructors=[
                        LeanConstructor(
                            name="mk",
                            fields=[LeanParam(name="x", type=LeanIdent("Int"))],
                        ),
                        LeanConstructor(name="bar", fields=[]),
                    ],
                )
            ],
        )
        out = generate_lean(m)
        assert "inductive Foo" in out
        assert "mk" in out
        assert "bar" in out

    def test_class_with_fields(self):
        m = LeanModule(
            imports=[],
            body=[
                LeanClass(
                    name="MyClass",
                    params=[],
                    extends=[],
                    fields=[LeanParam(name="x", type=LeanIdent("Int"))],
                )
            ],
        )
        out = generate_lean(m)
        assert "class MyClass" in out
        assert "x : Int" in out

    def test_instance_with_methods(self):
        m = LeanModule(
            imports=[],
            body=[
                LeanInstance(
                    name="myInst",
                    params=[],
                    type=LeanIdent("MyClass"),
                    methods=[
                        LeanDef(
                            name="x",
                            params=[],
                            return_type=LeanIdent("Int"),
                            value=LeanNum(42),
                        )
                    ],
                )
            ],
        )
        out = generate_lean(m)
        assert "instance myInst" in out
        assert "def x" in out

    def test_axiom(self):
        m = LeanModule(
            imports=[],
            body=[
                LeanAxiom(
                    name="foo",
                    params=[LeanParam(name="x", type=LeanIdent("Int"))],
                    type=LeanIdent("Bool"),
                )
            ],
        )
        out = generate_lean(m)
        assert "axiom foo" in out

    def test_example(self):
        m = LeanModule(
            imports=[], body=[LeanExample(expr=LeanBinOp(LeanNum(1), "+", LeanNum(2)))]
        )
        out = generate_lean(m)
        assert "#eval" in out

    def test_variable(self):
        m = LeanModule(
            imports=[],
            body=[LeanVariable(params=[LeanParam(name="x", type=LeanIdent("Int"))])],
        )
        out = generate_lean(m)
        assert "variable x : Int" in out or "variable (x : Int)" in out

    def test_namespace(self):
        m = LeanModule(
            imports=[],
            body=[
                LeanNamespace(
                    name="Foo",
                    commands=[
                        LeanDef(
                            name="bar",
                            params=[],
                            return_type=LeanIdent("Int"),
                            value=LeanNum(1),
                        )
                    ],
                )
            ],
        )
        out = generate_lean(m)
        assert "namespace Foo" in out
        assert "end Foo" in out

    def test_section_with_params(self):
        m = LeanModule(
            imports=[],
            body=[
                LeanSection(
                    params=[LeanParam(name="x", type=LeanIdent("Int"))], commands=[]
                )
            ],
        )
        out = generate_lean(m)
        assert "section" in out

    def test_theorem_and_lemma(self):
        thm = LeanDef(
            name="thm1",
            params=[],
            return_type=LeanIdent("Nat"),
            value=LeanNum(0),
            is_theorem=True,
        )
        lem = LeanDef(
            name="lem1",
            params=[],
            return_type=LeanIdent("Nat"),
            value=LeanNum(1),
            is_lemma=True,
        )
        m = LeanModule(imports=[], body=[thm, lem])
        out = generate_lean(m)
        assert "theorem thm1" in out
        assert "lemma lem1" in out

    def test_sig_only_def(self):
        d = LeanDef(
            name="f",
            params=[LeanParam(name="x", type=LeanIdent("Int"))],
            return_type=LeanIdent("Bool"),
            value=None,
        )
        m = LeanModule(imports=[], body=[d])
        out = generate_lean(m)
        assert "def f (x : Int) : Bool" in out

    def test_unknown_command_raises(self):
        class BogusCmd(LeanCommand):
            pass

        with pytest.raises(ValueError, match="Unknown command"):
            generate_lean(LeanModule(imports=[], body=[BogusCmd()]))


class TestLeanCodegenExprs:
    def test_char(self):
        m = LeanModule(
            imports=[],
            body=[LeanDef(name="c", params=[], return_type=None, value=LeanChar("a"))],
        )
        out = generate_lean(m)
        assert "'a'" in out

    def test_sort_with_level(self):
        m = LeanModule(
            imports=[],
            body=[
                LeanDef(
                    name="t",
                    params=[],
                    return_type=None,
                    value=LeanSort(level=LeanNum(1)),
                )
            ],
        )
        out = generate_lean(m)
        assert "Type" in out

    def test_unary_op_alpha(self):
        m = LeanModule(
            imports=[],
            body=[
                LeanDef(
                    name="f",
                    params=[],
                    return_type=None,
                    value=LeanUnaryOp(op="not", operand=LeanBool(True)),
                )
            ],
        )
        out = generate_lean(m)
        assert "not true" in out

    def test_type_arrow(self):
        m = LeanModule(
            imports=[],
            body=[
                LeanDef(
                    name="f",
                    params=[],
                    return_type=None,
                    value=LeanTypeArrow(
                        from_type=LeanIdent("Int"), to_type=LeanIdent("Bool")
                    ),
                )
            ],
        )
        out = generate_lean(m)
        assert "→" in out

    def test_type_spec(self):
        m = LeanModule(
            imports=[],
            body=[
                LeanDef(
                    name="f",
                    params=[],
                    return_type=None,
                    value=LeanTypeSpec(expr=LeanNum(5), type=LeanIdent("Int")),
                )
            ],
        )
        out = generate_lean(m)
        assert ":" in out or "Int" in out

    def test_forall_with_and_without_type(self):
        with_type = LeanForall(
            params=[LeanParam(name="x", type=LeanIdent("Int"))], body=LeanIdent("True")
        )
        without_type = LeanForall(
            params=[LeanParam(name="x", type=None)], body=LeanIdent("True")
        )
        m = LeanModule(
            imports=[],
            body=[
                LeanDef(name="a", params=[], return_type=None, value=with_type),
                LeanDef(name="b", params=[], return_type=None, value=without_type),
            ],
        )
        out = generate_lean(m)
        assert "∀" in out

    def test_pi(self):
        m = LeanModule(
            imports=[],
            body=[
                LeanDef(
                    name="f",
                    params=[],
                    return_type=None,
                    value=LeanPi(
                        binder=LeanParam(name="x", type=LeanIdent("Int")),
                        body=LeanIdent("Bool"),
                    ),
                )
            ],
        )
        out = generate_lean(m)
        assert "→" in out

    def test_list_lit(self):
        m = LeanModule(
            imports=[],
            body=[
                LeanDef(
                    name="xs",
                    params=[],
                    return_type=None,
                    value=LeanListLit(elts=[LeanNum(1), LeanNum(2)]),
                )
            ],
        )
        out = generate_lean(m)
        assert "[1, 2]" in out

    def test_tuple_lit(self):
        m = LeanModule(
            imports=[],
            body=[
                LeanDef(
                    name="t",
                    params=[],
                    return_type=None,
                    value=LeanTupleLit(elts=[LeanNum(1), LeanIdent("x")]),
                )
            ],
        )
        out = generate_lean(m)
        assert "(1, x)" in out

    def test_struct_inst_with_and_without_fields(self):
        with_fields = LeanStructInst(struct_name="Point", fields=[("x", LeanNum(1))])
        no_fields = LeanStructInst(struct_name="Point", fields=[])
        m = LeanModule(
            imports=[],
            body=[
                LeanDef(name="a", params=[], return_type=None, value=with_fields),
                LeanDef(name="b", params=[], return_type=None, value=no_fields),
            ],
        )
        out = generate_lean(m)
        assert "Point" in out

    def test_proj(self):
        m = LeanModule(
            imports=[],
            body=[
                LeanDef(
                    name="f",
                    params=[],
                    return_type=None,
                    value=LeanProj(expr=LeanIdent("p"), field="x"),
                )
            ],
        )
        out = generate_lean(m)
        assert "p.x" in out

    def test_have_with_name(self):
        have = LeanHave(
            name="h", type=LeanIdent("Nat"), value=LeanNum(1), body=LeanIdent("h")
        )
        m = LeanModule(
            imports=[],
            body=[LeanDef(name="f", params=[], return_type=None, value=have)],
        )
        out = generate_lean(m)
        assert "have h" in out

    def test_show(self):
        show = LeanShow(type=LeanIdent("Nat"), value=LeanNum(1))
        m = LeanModule(
            imports=[],
            body=[LeanDef(name="f", params=[], return_type=None, value=show)],
        )
        out = generate_lean(m)
        assert "show Nat" in out

    def test_calc(self):
        step = LeanCalcStep(relation=LeanIdent("="), value=LeanNum(2))
        calc = LeanCalc(steps=[step])
        m = LeanModule(
            imports=[],
            body=[LeanDef(name="f", params=[], return_type=None, value=calc)],
        )
        out = generate_lean(m)
        assert "calc" in out

    def test_do_all_branches(self):
        empty = LeanDo(stmts=[], last=None)
        stmts_only = LeanDo(stmts=[LeanDoLet(name="x", value=LeanNum(1))], last=None)
        last_only = LeanDo(stmts=[], last=LeanNum(42))
        both = LeanDo(stmts=[LeanDoLet(name="x", value=LeanNum(1))], last=LeanNum(42))
        bind = LeanDo(
            stmts=[
                LeanDoBind(
                    pattern=LeanPatternIdent("x"),
                    value=LeanApp(LeanIdent("f"), LeanNum(1)),
                )
            ],
            last=LeanIdent("x"),
        )
        do_expr = LeanDo(
            stmts=[LeanDoExpr(expr=LeanApp(LeanIdent("f"), LeanNum(1)))], last=None
        )
        m = LeanModule(
            imports=[],
            body=[
                LeanDef(name="e", params=[], return_type=None, value=empty),
                LeanDef(name="s", params=[], return_type=None, value=stmts_only),
                LeanDef(name="l", params=[], return_type=None, value=last_only),
                LeanDef(name="b", params=[], return_type=None, value=both),
                LeanDef(name="bd", params=[], return_type=None, value=bind),
                LeanDef(name="de", params=[], return_type=None, value=do_expr),
            ],
        )
        out = generate_lean(m)
        assert out.count("do") >= 6

    def test_by(self):
        by_expr = LeanBy(tactic=LeanIdent("simp"))
        m = LeanModule(
            imports=[],
            body=[LeanDef(name="f", params=[], return_type=None, value=by_expr)],
        )
        out = generate_lean(m)
        assert "by simp" in out

    def test_parenthesized(self):
        m = LeanModule(
            imports=[],
            body=[
                LeanDef(
                    name="f",
                    params=[],
                    return_type=None,
                    value=LeanParenthesized(expr=LeanNum(1)),
                )
            ],
        )
        out = generate_lean(m)
        assert "(1)" in out

    def test_named_arg(self):
        m = LeanModule(
            imports=[],
            body=[
                LeanDef(
                    name="f",
                    params=[],
                    return_type=None,
                    value=LeanNamedArg(name="x", value=LeanNum(1)),
                )
            ],
        )
        out = generate_lean(m)
        assert "x := 1" in out

    def test_gen_expr_none(self):
        m = LeanModule(
            imports=[],
            body=[LeanDef(name="f", params=[], return_type=None, value=None)],
        )
        out = generate_lean(m)
        assert "def f" in out

    def test_unknown_expr_raises(self):
        class BogusExpr(LeanExpr):
            pass

        d = LeanDef(name="f", params=[], return_type=None, value=BogusExpr())
        with pytest.raises(ValueError, match="Unknown expression"):
            generate_lean(LeanModule(imports=[], body=[d]))

    def test_unknown_pattern_raises(self):
        class BogusPattern(LeanPattern):
            pass

        from lp2.codegen.lean4_codegen import _gen_pattern

        with pytest.raises(ValueError, match="Unknown pattern"):
            _gen_pattern(BogusPattern())

    def test_pattern_ctor_with_subpatterns(self):
        pat = LeanPatternCtor(
            name="Foo", patterns=[LeanPatternIdent("a"), LeanPatternNum(1)]
        )
        from lp2.codegen.lean4_codegen import _gen_pattern

        result = _gen_pattern(pat)
        assert "Foo" in result
        assert "a" in result

    def test_pattern_struct(self):
        pat = LeanPatternStruct(name="Point", fields=[("x", LeanPatternWild())])
        from lp2.codegen.lean4_codegen import _gen_pattern

        result = _gen_pattern(pat)
        assert "Point" in result
        assert "x" in result


# ---------------------------------------------------------------------------
# python_codegen.py — direct AST construction → generate_python
# ---------------------------------------------------------------------------


class TestPyCodegenStatements:
    def test_ann_assign_with_and_without_value(self):
        with_val = PyAnnAssign(
            target=PyName("x"), annotation=PyName("int"), value=PyConstant(1)
        )
        no_val = PyAnnAssign(target=PyName("y"), annotation=PyName("int"), value=None)
        m = PyModule(
            body=[PyFunctionDef("f", [("z", None, None)], None, [with_val, no_val])]
        )
        code = generate_python(m)
        assert "x: int = 1" in code
        assert "y: int" in code

    def test_if_elif_else_chain(self):
        inner_if = PyIf(
            test=PyCompare(PyName("x"), ["=="], [PyConstant(2)]),
            body=[PyPass()],
            orelse=[],
        )
        outer_if = PyIf(
            test=PyCompare(PyName("x"), ["=="], [PyConstant(1)]),
            body=[PyPass()],
            orelse=[inner_if],
        )
        m = PyModule(
            body=[PyFunctionDef("f", [("x", PyName("int"), None)], None, [outer_if])]
        )
        code = generate_python(m)
        assert "elif" in code
        assert "if" in code

    def test_for_loop(self):
        m = PyModule(
            body=[
                PyFunctionDef(
                    "f",
                    [],
                    None,
                    [PyFor(target=PyName("i"), iter=PyName("items"), body=[PyPass()])],
                )
            ]
        )
        code = generate_python(m)
        assert "for i in items" in code

    def test_while_loop(self):
        m = PyModule(
            body=[
                PyFunctionDef(
                    "f", [], None, [PyWhile(test=PyConstant(True), body=[PyBreak()])]
                )
            ]
        )
        code = generate_python(m)
        assert "while True" in code
        assert "break" in code

    def test_continue(self):
        m = PyModule(
            body=[
                PyFunctionDef(
                    "f",
                    [],
                    None,
                    [
                        PyFor(
                            target=PyName("i"),
                            iter=PyName("items"),
                            body=[PyContinue()],
                        )
                    ],
                )
            ]
        )
        code = generate_python(m)
        assert "continue" in code

    def test_import(self):
        m = PyModule(body=[PyImport(names=["os", "sys"])])
        code = generate_python(m)
        assert "import os, sys" in code

    def test_try_except_else_finally(self):
        m = PyModule(
            body=[
                PyFunctionDef(
                    "f",
                    [],
                    None,
                    [
                        PyTry(
                            body=[PyPass()],
                            handlers=[
                                PyExceptHandler(
                                    typ=PyName("Exception"), name="e", body=[PyPass()]
                                )
                            ],
                            orelse=[PyPass()],
                            finalbody=[PyPass()],
                        )
                    ],
                )
            ]
        )
        code = generate_python(m)
        assert "try" in code
        assert "except" in code
        assert "else" in code
        assert "finally" in code

    def test_with_stmt(self):
        m = PyModule(
            body=[
                PyFunctionDef(
                    "f",
                    [],
                    None,
                    [PyWith(items=[(PyName("open"), PyName("f"))], body=[PyPass()])],
                )
            ]
        )
        code = generate_python(m)
        assert "with" in code

    def test_assert_with_and_without_msg(self):
        with_msg = PyAssert(
            test=PyCompare(PyName("x"), ["=="], [PyConstant(1)]), msg=PyConstant("bad")
        )
        no_msg = PyAssert(test=PyCompare(PyName("x"), [">"], [PyConstant(0)]), msg=None)
        m = PyModule(
            body=[
                PyFunctionDef("f1", [], None, [with_msg]),
                PyFunctionDef("f2", [], None, [no_msg]),
            ]
        )
        code = generate_python(m)
        assert "x == 1, " in code and "bad" in code
        assert "assert x > 0" in code

    def test_global_and_nonlocal(self):
        m = PyModule(
            body=[
                PyFunctionDef(
                    "f",
                    [],
                    None,
                    [
                        PyGlobal(names=["x"]),
                        PyNonlocal(names=["y"]),
                    ],
                )
            ]
        )
        code = generate_python(m)
        assert "global x" in code
        assert "nonlocal y" in code

    def test_delete(self):
        m = PyModule(
            body=[
                PyFunctionDef(
                    "f", [], None, [PyDelete(targets=[PyName("x"), PyName("y")])]
                )
            ]
        )
        code = generate_python(m)
        assert "del x, y" in code

    def test_type_alias(self):
        m = PyModule(body=[PyTypeAlias(name=PyName("Vector"), value=PyName("list"))])
        code = generate_python(m)
        assert "type Vector = list" in code

    def test_empty_class_body(self):
        m = PyModule(body=[PyClassDef(name="Empty", bases=[], body=[])])
        code = generate_python(m)
        assert "class Empty:" in code
        assert "pass" in code

    def test_empty_function_body(self):
        m = PyModule(body=[PyFunctionDef("f", [], None, [])])
        code = generate_python(m)
        assert "def f():" in code
        assert "pass" in code

    def test_nested_if_elif_else_chain(self):
        elif_chain = PyIf(
            test=PyCompare(PyName("x"), ["=="], [PyConstant(1)]),
            body=[PyPass()],
            orelse=[
                PyIf(
                    test=PyCompare(PyName("x"), ["=="], [PyConstant(2)]),
                    body=[PyPass()],
                    orelse=[PyPass()],
                )
            ],
        )
        code = generate_python(
            PyModule(
                body=[
                    PyFunctionDef("f", [("x", PyName("int"), None)], None, [elif_chain])
                ]
            )
        )
        assert "elif" in code


class TestPyCodegenExprs:
    def test_yield_and_yield_from(self):
        m = PyModule(
            body=[
                PyFunctionDef(
                    "gen",
                    [("n", PyName("int"), None)],
                    PyName("int"),
                    [
                        PyExprStmt(expr=PyYield(value=PyName("n"))),
                        PyExprStmt(expr=PyYieldFrom(value=PyName("other"))),
                    ],
                )
            ]
        )
        code = generate_python(m)
        assert "yield n" in code
        assert "yield from" in code

    def test_await(self):
        m = PyModule(
            body=[
                PyFunctionDef(
                    "f",
                    [],
                    None,
                    [
                        PyReturn(
                            value=PyAwait(
                                value=PyCall(func=PyName("get"), args=[PyName("url")])
                            )
                        ),
                    ],
                )
            ]
        )
        code = generate_python(m)
        assert "await" in code

    def test_starred(self):
        m = PyModule(
            body=[
                PyFunctionDef(
                    "f",
                    [],
                    None,
                    [
                        PyReturn(
                            value=PyCall(
                                func=PyName("foo"),
                                args=[PyStarred(value=PyName("items"))],
                            )
                        ),
                    ],
                )
            ]
        )
        code = generate_python(m)
        assert "*items" in code

    def test_set_literal(self):
        m = PyModule(
            body=[
                PyFunctionDef(
                    "f",
                    [],
                    None,
                    [
                        PyReturn(value=PySet(elts=[PyConstant(1), PyConstant(2)])),
                    ],
                )
            ]
        )
        code = generate_python(m)
        assert "{1, 2}" in code

    def test_dict_comp(self):
        comp = PyDictComp(
            key=PyName("k"),
            value=PyName("v"),
            generators=[
                PyComprehension(target=PyName("k"), iter=PyName("items"), ifs=[])
            ],
        )
        m = PyModule(
            body=[
                PyFunctionDef(
                    "f",
                    [],
                    None,
                    [
                        PyReturn(value=comp),
                    ],
                )
            ]
        )
        code = generate_python(m)
        assert "for k in items" in code

    def test_list_comp_and_set_comp(self):
        gen = [PyComprehension(target=PyName("x"), iter=PyName("items"), ifs=[])]
        lc = PyListComp(elt=PyName("x"), generators=gen)
        sc = PySetComp(elt=PyName("x"), generators=gen)
        m = PyModule(
            body=[
                PyFunctionDef(
                    "f",
                    [],
                    None,
                    [
                        PyReturn(value=lc),
                        PyReturn(value=sc),
                    ],
                )
            ]
        )
        code = generate_python(m)
        assert "[x for x in items]" in code or "[x for x" in code
        assert "{x for x in items}" in code or "{x for x" in code

    def test_walrus(self):
        m = PyModule(
            body=[
                PyFunctionDef(
                    "f",
                    [],
                    None,
                    [
                        PyExprStmt(
                            expr=PyWalrus(target=PyName("x"), value=PyConstant(1))
                        ),
                    ],
                )
            ]
        )
        code = generate_python(m)
        assert "x := 1" in code

    def test_bytes_constant(self):
        m = PyModule(
            body=[
                PyFunctionDef(
                    "f",
                    [],
                    None,
                    [
                        PyReturn(value=PyConstant(value=b"hello")),
                    ],
                )
            ]
        )
        code = generate_python(m)
        assert "b'hello'" in code or 'b"hello"' in code

    def test_expr_none_fallback(self):
        from lp2.codegen.python_codegen import _gen_expr

        assert _gen_expr(None) == "None"

    def test_unknown_expr_raises(self):
        from lp2.codegen.python_codegen import _gen_expr

        class BogusExpr(PyExpr):
            pass

        with pytest.raises(ValueError, match="Unknown expression"):
            _gen_expr(BogusExpr())

    def test_gen_pattern_py_fallbacks(self):
        from lp2.codegen.python_codegen import _gen_pattern_py

        assert _gen_pattern_py(PyName("x")) == "x"
        assert _gen_pattern_py(PyConstant(True)) == "True"
        assert _gen_pattern_py(PyConstant(None)) == "None"
        assert (
            _gen_pattern_py(PyMatchOr(patterns=[PyConstant(1), PyConstant(2)]))
            == "1 | 2"
        )
        assert (
            _gen_pattern_py(PyCall(func=PyName("int"), args=[PyName("x")])) == "int(x)"
        )


# ---------------------------------------------------------------------------
# lean4_to_python.py — public API with Lean source strings
# ---------------------------------------------------------------------------


class TestLeanToPyTranspiler:
    def test_open_variable_filtered(self):
        """Lean commands that convert to None should be filtered out."""
        result = lean_to_py("variable (x : Int)\ndef f : Int := x\n")
        assert result

    def test_namespace(self):
        result = lean_to_py("namespace Foo\ndef f : Int := 1\nend Foo\n")
        assert result

    def test_structure_inductive_have(self):
        result = lean_to_py("""
structure Point where
  x : Int
  y : Int

inductive Color where
  | red
  | blue

def f : Int :=
  have h : Int := 1;
  h
""")
        assert result

    def test_inductive_with_ctor_fields(self):
        result = lean_to_py("inductive Foo : Type where\n  | mk : Int → Foo\n  | bar\n")
        assert result

    def test_if_without_else(self):
        result = lean_to_py("def f (x : Int) : Int := if x > 0 then x\n")
        assert result

    def test_match_bool_ctor_patterns(self):
        result = lean_to_py(
            "def f (b : Bool) : Int := match b with\n  | true => 1\n  | false => 0\n"
        )
        assert result

    def test_pattern_ctor_or(self):
        result = lean_to_py("""
def f (x : Int) : Int :=
  match x with
  | 0 => 1
  | a => a
""")
        assert result

    def test_true_false_as_stmts(self):
        result = lean_to_py("""
def f : Bool :=
  let x := true;
  x
""")
        assert result

    def test_cons_app(self):
        result = lean_to_py("def f : List Int := 1 :: 2 :: []\n")
        assert result

    def test_type_apps(self):
        result = lean_to_py("""
def f (m : HashMap Int String) : Unit := ()
def g (s : Set Int) : Unit := ()
""")
        assert result

    def test_lean_type_none(self):
        result = lean_to_py("def f (x : Int) := x\n")
        assert result

    def test_empty_arms_match(self):
        result = lean_to_py(
            "def f : Int := match true with\n  | true => 1\n  | false => 0\n"
        )
        assert result

    def test_lean_to_py_unknown_command(self):
        from lp2.transpiler.lean4_to_python import _cmd_to_stmt

        class BogusCmd(LeanCommand):
            pass

        result = _cmd_to_stmt(BogusCmd())
        assert result is None

    def test_expr_py_ident_special_names(self):
        from lp2.transpiler.lean4_to_python import _expr_to_py

        assert isinstance(_expr_to_py(LeanIdent("none")), PyConstant)
        assert isinstance(_expr_to_py(LeanIdent("true")), PyConstant)
        assert isinstance(_expr_to_py(LeanIdent("false")), PyConstant)

    def test_expr_to_py_none_fallback(self):
        from lp2.transpiler.lean4_to_python import _expr_to_py

        result = _expr_to_py(None)
        assert result is None or isinstance(result, PyConstant)

    def test_lean_type_none_fallback(self):
        from lp2.transpiler.lean4_to_python import _lean_type_to_py

        result = _lean_type_to_py(None)
        assert isinstance(result, PyName)

    def test_structure_no_annot_field(self):
        from lp2.codegen.python_codegen import generate_python
        from lp2.transpiler.lean4_to_python import lean_to_py as _lp

        s = LeanStructure(
            name="Point", params=[], extends=[], fields=[LeanParam(name="x", type=None)]
        )
        m = LeanModule(imports=[], body=[s])
        result = generate_python(_lp(m))
        assert "x" in result

    def test_prod_mk_two_elements(self):
        from lp2.transpiler.lean4_to_python import _expr_to_py

        app = LeanApp(
            func=LeanApp(func=LeanIdent("Prod.mk"), arg=LeanNum(1)), arg=LeanNum(2)
        )
        result = _expr_to_py(app)
        assert isinstance(result, PyTuple)
        assert len(result.elts) == 2

    def test_ensure_return_edge_cases(self):
        from lp2.transpiler.lean4_to_python import _ensure_return

        assert len(_ensure_return([])) == 1
        assert isinstance(_ensure_return([])[0], PyReturn)
        assert _ensure_return([PyReturn(value=PyConstant(1))])[0].value.value == 1
        result = _ensure_return([PyExprStmt(expr=PyConstant(42))])
        assert isinstance(result[0], PyReturn)
        assert result[0].value.value == 42


# ---------------------------------------------------------------------------
# lean_parser.py — edge case Lean sources
# ---------------------------------------------------------------------------


class TestLeanParserEdgeCases:
    def test_inductive_structure_class_axiom(self):
        result = lean_to_py("""
inductive MyOption (α : Type) : Type where
  | some : α → MyOption α
  | none : MyOption α

structure Box (α : Type) where
  val : α

class Monad (m : Type → Type) where
  bind : m α → (α → m β) → m β

axiom choice : Bool
""")
        assert result

    def test_instance_with_methods(self):
        result = lean_to_py("""
class Add (a : Type) where
  add : a → a → a

instance : Add Int where
  add x y := x + y
""")
        assert result

    def test_section_and_let_chain(self):
        result = lean_to_py("""
section
def f (x : Int) : Int := x + 1
end
""")
        assert result

    def test_example_eval(self):
        result = lean_to_py("#eval 1 + 2\n")
        assert result

    def test_multiline_let(self):
        result = lean_to_py("""
def f (x : Int) : Int :=
  let a := x + 1;
  let b := a * 2;
  b
""")
        assert result

    def test_while_loop_as_string(self):
        result = lean_to_py("""
partial def f (x : Int) : Int :=
  if x > 0 then f (x - 1) else 0
""")
        assert result


# ---------------------------------------------------------------------------
# python_to_lean4.py — more Python source coverage
# ---------------------------------------------------------------------------


class TestPyToLeanEdgeCases:
    def test_set_and_comprehension(self):
        result = py_to_lean("def f() -> set:\n    return {1, 2, 3}\n")
        assert result

    def test_nested_assign(self):
        result = py_to_lean("""
def f() -> int:
    x = 1
    y = x + 1
    return y
""")
        assert result

    def test_if_elif_expr(self):
        result = py_to_lean("""
def f(x: int) -> str:
    if x > 0:
        return "pos"
    elif x < 0:
        return "neg"
    return "zero"
""")
        assert result

    def test_unnamed_ast_node_type(self):
        from lp2.ast.python_ast import PyNode

        class BogusNode(PyNode):
            pass

        from lp2.transpiler.python_to_lean4 import _expr_to_lean

        result = _expr_to_lean(BogusNode())
        assert isinstance(result, LeanHole)

    def test_unknown_stmt_raises(self):
        from lp2.codegen.python_codegen import _gen_stmt

        class BogusStmt(PyStmt):
            pass

        with pytest.raises(ValueError, match="Unknown statement"):
            _gen_stmt(BogusStmt())

    def test_raise_with_and_without_exc(self):
        from lp2.codegen.python_codegen import generate_python

        m = PyModule(
            body=[
                PyFunctionDef("f", [], None, [PyRaise(exc=None)]),
                PyFunctionDef("g", [], None, [PyRaise(exc=PyName("e"))]),
            ]
        )
        code = generate_python(m)
        assert "raise\n" in code or "raise" in code
        assert "raise e" in code
