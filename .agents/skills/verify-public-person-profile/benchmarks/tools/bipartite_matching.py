"""
Kuhn-Munkres (Hungarian Algorithm) for Maximum Weight Partial Bipartite Matching.
Pure Python O(N^3) implementation with dummy node expansion, admissible edge filtering,
and zero external dependencies.
"""

from typing import List, Tuple


def hungarian_min_cost(cost: List[List[float]]) -> Tuple[List[int], float]:
    """
    Solves min-cost assignment for an N x N cost matrix using potentials.
    Time complexity: O(N^3).
    Returns (row_to_col, total_cost).
    """
    n = len(cost)
    if n == 0:
        return [], 0.0

    u = [0.0] * (n + 1)
    v = [0.0] * (n + 1)
    p = [0] * (n + 1)
    way = [0] * (n + 1)

    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [float("inf")] * (n + 1)
        used = [False] * (n + 1)
        while True:
            used[j0] = True
            i0 = p[j0]
            delta = float("inf")
            j1 = 0
            for j in range(1, n + 1):
                if not used[j]:
                    cur = cost[i0 - 1][j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j] = cur
                        way[j] = j0
                    if minv[j] < delta:
                        delta = minv[j]
                        j1 = j
            for j in range(0, n + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break

    ans = [0] * n
    for j in range(1, n + 1):
        if p[j] != 0:
            ans[p[j] - 1] = j - 1

    total_cost = sum(cost[i][ans[i]] for i in range(n))
    return ans, total_cost


def max_weight_partial_matching(
    weight_matrix: List[List[float]],
    threshold: float = 1.0,
) -> Tuple[List[Tuple[int, int]], float]:
    """
    Finds the maximum weight matching between m items and n items.
    Expands the matrix to N x N with dummy nodes (where N = max(m, n)).
    Only pairs with weight >= threshold are included in admissible matches.
    
    Returns:
      (admissible_matches, total_weight_of_admissible_matches)
      where admissible_matches is a list of (row_idx, col_idx).
    """
    m = len(weight_matrix)
    if m == 0:
        return [], 0.0
    n = len(weight_matrix[0]) if m > 0 else 0
    if n == 0:
        return [], 0.0

    n_dim = max(m, n)
    max_w = 0.0
    for row in weight_matrix:
        for val in row:
            if val > max_w:
                max_w = val

    # Convert max weight to min cost: cost = max_w - weight
    cost = [[max_w for _ in range(n_dim)] for _ in range(n_dim)]
    for i in range(m):
        for j in range(n):
            cost[i][j] = max_w - weight_matrix[i][j]

    assignment, _ = hungarian_min_cost(cost)

    admissible_matches = []
    total_admissible_weight = 0.0

    for i in range(m):
        j = assignment[i]
        if j < n:
            w = weight_matrix[i][j]
            if w >= threshold:
                admissible_matches.append((i, j))
                total_admissible_weight += w

    return admissible_matches, total_admissible_weight
