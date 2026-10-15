# Python sets

1. A set holds each value once, in no fixed order. `{1, 2, 2}` is `{1, 2}`.
2. `a | b` is the union: every value in `a`, in `b`, or in both. `a.union(b)` gives the same set.
3. `a & b` is the intersection: only the values in both.
4. `{*a, *b}` unpacks both sets into a new set literal, so it also gives the union.
5. `a - b` is the difference: values in `a` that are not in `b`.
