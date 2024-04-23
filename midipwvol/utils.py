def lerp(value, a, b, x, y):
    """Linear interpolation of value from the a~b range to the x~y range.

    >>> lerp(0, 0.0, 1.0, 3.0, 6.0)
    3.0
    >>> lerp(0.5, 0.0, 1.0, 3.0, 6.0)
    4.5
    >>> lerp(75, 50, 100, 7, 9)
    8.0
    """
    return x + (y - x) * (value - a) / (b - a)


def interp(value:int|float, pairs:list[tuple]):
    """Linear interpolation of one value against a list of values.

    Inspired by numpy.interp().

    >>> func = [(0, 0.0), (25, 0.0), (75, 1.0), (100, 1.0)]
    >>> interp(0, func)
    0.0
    >>> interp(20, func)
    0.0
    >>> interp(25, func)
    0.0
    >>> interp(30, func)
    0.1
    >>> interp(35, func)
    0.2
    >>> interp(45, func)
    0.4
    >>> interp(50, func)
    0.5
    >>> interp(55, func)
    0.6
    >>> interp(70, func)
    0.9
    >>> interp(75, func)
    1.0
    >>> interp(76, func)
    1.0
    >>> interp(99, func)
    1.0
    >>> interp(100, func)
    1.0

    How should out-of-bounds behave?
    * Repeat the boundary value as a constant.
    * LERP against the first or the last segment.
    * Throw a ValueError.
    >>> interp(-1, func)
    ValueError: ...
    >>> interp(101, func)
    ValueError: ...

    The first element of each pair should be in increasing order,
    but this is not checked.
    """
    for ((a, x), (b, y)) in zip(pairs[:-1], pairs[1:]):
        if value == a:
            return x
        elif value == b:
            return y
        elif a <= value <= b:
            return lerp(value, a, b, x, y)
    raise ValueError("value out of bounds of pairs")
