import math
import sys
import time
from functools import lru_cache

# no_transpile
sys.set_int_max_str_digits(100000)

# ============================================================
# 1. Naive iterative factorial
# ============================================================

def factorial_iterative(n: int) -> int:
    r = 1
    for i in range(2, n + 1):
        r *= i
    return r


# ============================================================
# 2. Divide-and-conquer product tree factorial
# ============================================================

def product_range(lo: int, hi: int) -> int:
    if lo > hi:
        return 1

    if lo == hi:
        return lo

    if hi - lo == 1:
        return lo * hi

    mid = (lo + hi) // 2

    return product_range(lo, mid) * product_range(mid + 1, hi)


def factorial_product_tree(n: int) -> int:
    if n < 2:
        return 1

    return product_range(1, n)


# ============================================================
# 3. Prime-factorization factorial
# ============================================================

@no_transpile
def sieve(n: int):
    if n < 2:
        return []

    bs = bytearray(b"\x01") * (n + 1)
    bs[0:2] = b"\x00\x00"

    limit = int(n**0.5)

    for p in range(2, limit + 1):
        if bs[p]:
            start = p * p
            bs[start:n+1:p] = b"\x00" * (((n - start) // p) + 1)

    return [i for i in range(2, n + 1) if bs[i]]


@no_transpile
@lru_cache(maxsize=None)
def primes_cached(n: int):
    return tuple(sieve(n))


@no_transpile
def factorial_prime(n: int) -> int:
    if n < 2:
        return 1

    result = 1

    for p in primes_cached(n):
        e = 0
        q = n

        while q:
            q //= p
            e += q

        result *= pow(p, e)

    return result


# ============================================================
# 4. Simplified PrimeSwing factorial
# ============================================================


@no_transpile
def odd_swing(n: int) -> int:
    if n < 2:
        return 1

    result = 1

    for p in primes_cached(n):
        if p == 2:
            continue
        q = n

        while q:
            q //= p
            if q & 1:
                result *= p

    return result


@no_transpile
def odd_factorial(n: int) -> int:
    if n < 2:
        return 1

    return odd_factorial(n // 2) ** 2 * odd_swing(n)


@no_transpile
def factorial_primeswing(n: int) -> int:
    if n < 2:
        return 1

    odd = odd_factorial(n)

    # exponent of 2 in n!
    two_exp = n - bin(n).count("1")

    return odd << two_exp


# ============================================================
# 5. Builtin factorial
# ============================================================

def factorial_builtin(n: int) -> int:
    return math.factorial(n)


# ============================================================
# Benchmark helper
# ============================================================

@no_transpile
def benchmark(fn, n, repeat=3):
    times = []

    result = None

    for _ in range(repeat):
        t0 = time.perf_counter()
        result = fn(n)
        t1 = time.perf_counter()

        times.append(t1 - t0)

    return {
        "function": fn.__name__,
        "best": min(times),
        "avg": sum(times) / len(times),
        "digits": len(str(result)),
    }


# ============================================================
# Main benchmark
# ============================================================

@no_transpile
def __main__bench():
    ns = [1000, 5000, 10000, 20000]

    functions = [
        factorial_iterative,
        factorial_product_tree,
        factorial_prime,
        factorial_primeswing,
        factorial_builtin,
    ]

    for n in ns:

        print("=" * 72)
        print(f"n = {n}")
        print("=" * 72)

        reference = math.factorial(n)

        for fn in functions:
            r = fn(n)
            assert r == reference, f"{fn.__name__} failed correctness test"

        print(f"Correctness verified for n={n}\n")

        rows = []

        for fn in functions:
            rows.append(benchmark(fn, n))

        rows.sort(key=lambda x: x["best"])

        for row in rows:
            print(
                f"{row['function']:28s} "
                f"best={row['best']:.6f}s "
                f"avg={row['avg']:.6f}s "
                f"digits={row['digits']}"
            )

        print()


@no_transpile
def __main__():
    __main__bench()
