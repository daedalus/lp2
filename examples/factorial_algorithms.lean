partial def factorial (n : Nat) : Nat :=
  let result := 1; let rec loop (i : Nat) (result : Nat) : Nat := if i < n + 1 then loop (i + 1) (result * i) else result; loop 2 result

-- no_transpile (# no_transpile at line 7)
--   sys.set_int_max_str_digits(100000)

partial def factorial_iterative (n : Nat) : Nat :=
  let r := 1; let rec loop (i : Nat) (r : Nat) : Nat := if i < n + 1 then loop (i + 1) (r * i) else r; loop 2 r

partial def product_range (lo : Nat) (hi : Nat) : Nat :=
  if lo > hi then 1 else if lo == hi then lo else if hi - lo == 1 then lo * hi else let mid := (lo + hi) / 2; product_range lo mid * product_range (mid + 1) hi

def factorial_product_tree (n : Nat) : Nat :=
  if n < 2 then 1 else product_range 1 n

-- no_transpile (@sieve)
--   def sieve(n: int):
--       if n < 2:
--           return []
--   
--       bs = bytearray(b"\x01") * (n + 1)
--       bs[0:2] = b"\x00\x00"
--   
--       limit = int(n**0.5)
--   
--       for p in range(2, limit + 1):
--           if bs[p]:
--               start = p * p
--               bs[start:n+1:p] = b"\x00" * (((n - start) // p) + 1)
--   
--       return [i for i in range(2, n + 1) if bs[i]]

-- no_transpile (@primes_cached)
--   def primes_cached(n: int):
--       return tuple(sieve(n))

-- no_transpile (@factorial_prime)
--   def factorial_prime(n: int) -> int:
--       if n < 2:
--           return 1
--   
--       result = 1
--   
--       for p in primes_cached(n):
--           e = 0
--           q = n
--   
--           while q:
--               q //= p
--               e += q
--   
--           result *= pow(p, e)
--   
--       return result

-- no_transpile (@odd_swing)
--   def odd_swing(n: int) -> int:
--       if n < 2:
--           return 1
--   
--       result = 1
--   
--       for p in primes_cached(n):
--           if p == 2:
--               continue
--           q = n
--   
--           while q:
--               q //= p
--               if q & 1:
--                   result *= p
--   
--       return result

-- no_transpile (@odd_factorial)
--   def odd_factorial(n: int) -> int:
--       if n < 2:
--           return 1
--   
--       return odd_factorial(n // 2) ** 2 * odd_swing(n)

-- no_transpile (@factorial_primeswing)
--   def factorial_primeswing(n: int) -> int:
--       if n < 2:
--           return 1
--   
--       odd = odd_factorial(n)
--   
--       # exponent of 2 in n!
--       two_exp = n - bin(n).count("1")
--   
--       return odd << two_exp

def factorial_builtin (n : Nat) : Nat :=
  factorial n

-- no_transpile (@benchmark)
--   def benchmark(fn, n, repeat=3):
--       times = []
--   
--       result = None
--   
--       for _ in range(repeat):
--           t0 = time.perf_counter()
--           result = fn(n)
--           t1 = time.perf_counter()
--   
--           times.append(t1 - t0)
--   
--       return {
--           "function": fn.__name__,
--           "best": min(times),
--           "avg": sum(times) / len(times),
--           "digits": len(str(result)),
--       }

-- no_transpile (@__main__bench)
--   def __main__bench():
--       ns = [1000, 5000, 10000, 20000]
--   
--       functions = [
--           factorial_iterative,
--           factorial_product_tree,
--           factorial_prime,
--           factorial_primeswing,
--           factorial_builtin,
--       ]
--   
--       for n in ns:
--   
--           print("=" * 72)
--           print(f"n = {n}")
--           print("=" * 72)
--   
--           reference = math.factorial(n)
--   
--           for fn in functions:
--               r = fn(n)
--               assert r == reference, f"{fn.__name__} failed correctness test"
--   
--           print(f"Correctness verified for n={n}\n")
--   
--           rows = []
--   
--           for fn in functions:
--               rows.append(benchmark(fn, n))
--   
--           rows.sort(key=lambda x: x["best"])
--   
--           for row in rows:
--               print(
--                   f"{row['function']:28s} "
--                   f"best={row['best']:.6f}s "
--                   f"avg={row['avg']:.6f}s "
--                   f"digits={row['digits']}"
--               )
--   
--           print()

-- no_transpile (@__main__)
--   def __main__():
--       __main__bench()
