def bubble_sort(xs: list[int]) -> list[int]:
    """Sort a list using bubble sort."""
    i = 0
    n = len(xs)
    while i < n:
        j = 0
        while j < n - 1:
            if xs[j] > xs[j + 1]:
                temp = xs[j]
                xs[j] = xs[j + 1]
                xs[j + 1] = temp
            j += 1
        i += 1
    return xs
