# Counting loop steps

1. `range(a, b)` gives a, a+1, ..., b-1. It stops before b, so it has b - a values.
2. `range(a, b, s)` counts up from a in steps of s, still stopping before b.
3. A loop over n items whose body does a fixed number of steps, k, does k x n steps in all. We call that O(n): big-O drops the fixed factor.
4. A loop inside a loop multiplies: if the outer loop runs n times and the inner loop runs m times for each, the inner body runs n x m times. Two loops over n, one inside the other, are O(n^2).
5. Two loops one after the other add: n + m steps.
6. An inner loop with a fixed count, like `range(3)`, is a fixed factor, so the whole thing stays O(n).
