def fermat_factorization(n: int) -> tuple[int, int]:
    """Factor an integer using Fermat's factorization method."""
    if n % 2 == 0:
        return (2, n // 2)
    x = int(n**0.5)
    if x * x < n:
        x += 1
    while True:
        y_squared = x * x - n
        y = int(y_squared**0.5)
        if y * y == y_squared:
            return (x - y, x + y)
        x += 1
