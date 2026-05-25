def count(n: int) -> list[int]:
    i = 0
    while i < n:
        yield i
        i = i + 1


def evens(xs: list[int]) -> list[int]:
    for x in xs:
        if x % 2 == 0:
            yield x


def take_first(xs: list[int]) -> list[int]:
    if xs != []:
        yield xs[0]
    else:
        yield 0
