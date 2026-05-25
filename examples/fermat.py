def isqrt(n: int) -> int:
    """Integer square root (floor of sqrt)."""
    if n < 2:
        return n
    x = n // 2
    while True:
        x1 = (x + n // x) // 2
        if x1 >= x:
            return x
        x = x1


def fermat_factorization(n: int) -> tuple[int, int]:
    """Factor n using Fermat's factorization method."""
    if n % 2 == 0:
        return (2, n // 2)
    x = isqrt(n)
    if x * x < n:
        x += 1
    while True:
        y_sq = x * x - n
        y = isqrt(y_sq)
        if y * y == y_sq:
            return (x - y, x + y)
        x += 1
