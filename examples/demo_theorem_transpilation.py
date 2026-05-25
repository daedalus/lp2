#!/usr/bin/env python3
"""
Demo: Transpiling well-known mathematical theorems from Lean 4 to Python
using the lp2 bidirectional transpiler.

This demonstrates how to represent mathematical properties as computable
functions in Lean that can be transpiled to Python.
"""

from lp2 import lean_to_py

def main():
    print("=== LP2: Lean 4 ↔ Python Bidirectional Transpiler ===\n")

    # Example 1: Commutativity of Addition as a Boolean Property
    print("1. Commutativity of Addition: a + b = b + a")
    print("-" * 50)

    lean_source = '''
def add_comm_prop (a b : Int) : Bool := (a + b = b + a)
'''

    print("Lean 4 source:")
    print(lean_source.strip())

    # Transpile to Python
    py_source = lean_to_py(lean_source)
    print("\nTranspiled Python source:")
    print(py_source.strip())

    # Execute and test
    print("Testing the transpiled function:")
    namespace = {}
    exec(py_source, namespace)  # This defines add_comm_prop in namespace
    add_comm_prop = namespace['add_comm_prop']

    test_cases = [
        (0, 0),
        (1, 2),
        (-3, 5),
        (100, -100),
        (-5, -7)
    ]

    for a, b in test_cases:
        result = add_comm_prop(a, b)
        print(f"  add_comm_prop({a:4}, {b:4}) = {result}")

    print("\n" + "="*60 + "\n")

    # Example 2: Associativity of Addition
    print("2. Associativity of Addition: (a + b) + c = a + (b + c)")
    print("-" * 50)

    lean_source2 = '''
def add_assoc_prop (a b c : Int) : Bool := ((a + b) + c) = (a + (b + c))
'''

    print("Lean 4 source:")
    print(lean_source2.strip())

    py_source2 = lean_to_py(lean_source2)
    print("\nTranspiled Python source:")
    print(py_source2.strip())

    print("Testing the transpiled function:")
    namespace2 = {}
    exec(py_source2, namespace2)
    add_assoc_prop = namespace2['add_assoc_prop']

    test_cases2 = [
        (0, 0, 0),
        (1, 2, 3),
        (-1, 5, -3),
        (10, -5, 7)
    ]

    for a, b, c in test_cases2:
        result = add_assoc_prop(a, b, c)
        print(f"  add_assoc_prop({a:3}, {b:3}, {c:3}) = {result}")

    print("\n" + "="*60 + "\n")

    # Example 3: Additive Identity
    print("3. Additive Identity: a + 0 = a")
    print("-" * 50)

    lean_source3 = '''
def add_zero_prop (a : Int) : Bool := (a + 0 = a)
'''

    print("Lean 4 source:")
    print(lean_source3.strip())

    py_source3 = lean_to_py(lean_source3)
    print("\nTranspiled Python source:")
    print(py_source3.strip())

    print("Testing the transpiled function:")
    namespace3 = {}
    exec(py_source3, namespace3)
    add_zero_prop = namespace3['add_zero_prop']

    test_cases3 = [0, 1, -5, 100, -42]

    for a in test_cases3:
        result = add_zero_prop(a)
        print(f"  add_zero_prop({a:4}) = {result}")

    print("\n" + "="*60 + "\n")

    # Example 4: Multiplicative Commutativity
    print("4. Multiplicative Commutativity: a * b = b * a")
    print("-" * 50)

    lean_source4 = '''
def mul_comm_prop (a b : Int) : Bool := (a * b = b * a)
'''

    print("Lean 4 source:")
    print(lean_source4.strip())

    py_source4 = lean_to_py(lean_source4)
    print("\nTranspiled Python source:")
    print(py_source4.strip())

    print("Testing the transpiled function:")
    namespace4 = {}
    exec(py_source4, namespace4)
    mul_comm_prop = namespace4['mul_comm_prop']

    test_cases4 = [
        (0, 0),
        (1, 2),
        (-3, 5),
        (100, -100),
        (-5, -7)
    ]

    for a, b in test_cases4:
        result = mul_comm_prop(a, b)
        print(f"  mul_comm_prop({a:4}, {b:4}) = {result}")

    print("\n" + "="*60 + "\n")

    # Example 5: Multiplicative Associativity
    print("5. Multiplicative Associativity: a * (b * c) = (a * b) * c")
    print("-" * 50)

    lean_source5 = '''
def mul_assoc_prop (a b c : Int) : Bool := (a * (b * c)) = ((a * b) * c)
'''

    print("Lean 4 source:")
    print(lean_source5.strip())

    py_source5 = lean_to_py(lean_source5)
    print("\nTranspiled Python source:")
    print(py_source5.strip())

    print("Testing the transpiled function:")
    namespace5 = {}
    exec(py_source5, namespace5)
    mul_assoc_prop = namespace5['mul_assoc_prop']

    test_cases5 = [
        (0, 0, 0),
        (1, 2, 3),
        (-1, 5, -3),
        (10, -5, 7),
        (2, 3, 4)
    ]

    for a, b, c in test_cases5:
        result = mul_assoc_prop(a, b, c)
        print(f"  mul_assoc_prop({a:3}, {b:3}, {c:3}) = {result}")

    print("\n" + "="*60 + "\n")

    # Example 6: Multiplicative Identity
    print("6. Multiplicative Identity: a * 1 = a")
    print("-" * 50)

    lean_source6 = '''
def mul_one_prop (a : Int) : Bool := (a * 1 = a)
'''

    print("Lean 4 source:")
    print(lean_source6.strip())

    py_source6 = lean_to_py(lean_source6)
    print("\nTranspiled Python source:")
    print(py_source6.strip())

    print("Testing the transpiled function:")
    namespace6 = {}
    exec(py_source6, namespace6)
    mul_one_prop = namespace6['mul_one_prop']

    test_cases6 = [0, 1, -5, 100, -42]

    for a in test_cases6:
        result = mul_one_prop(a)
        print(f"  mul_one_prop({a:4}) = {result}")

    print("\n" + "="*60)
    print("Demo completed successfully!")

if __name__ == "__main__":
    main()
