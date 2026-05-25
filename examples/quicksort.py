def quicksort(xs: list[int]) -> list[int]:
    if len(xs) <= 1:
        return xs
    pivot = xs[0]
    less = []
    equal = []
    greater = []
    for x in xs:
        if x < pivot:
            less = less + [x]
        elif x == pivot:
            equal = equal + [x]
        else:
            greater = greater + [x]
    return quicksort(less) + equal + quicksort(greater)
