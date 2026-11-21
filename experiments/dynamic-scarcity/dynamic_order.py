#!/usr/bin/env python3
"""Standalone minimal value-order candidate, pure Python only.

Main integration replaces just the static ranks key at a non-forced DFS node.
Coverage, candidate pool, MRV row selection, cutoff, memo and time limit stay fixed.
"""


def order_choices(choices, candidate_rows, adj, active, minimum, base_ranks):
    """base_ranks[p] = seed's random noise + 0.35 * candidate row count."""
    current = {}
    def key(p):
        scarcity = 0.0
        for r in candidate_rows[p]:
            degree = current.get(r)
            if degree is None:
                degree = (active & adj[r]).bit_count()
                current[r] = degree
            scarcity += 1.0 / degree
        return base_ranks[p] + minimum * scarcity
    return sorted(choices, key=key, reverse=True)


def small_asserts():
    rows = [[0,1], [0,2], [1,3], [2,3], [1,4], [2,4], [3,4], [1,5], [2,5], [3,5], [4,5]]
    adj = [0]*6
    for p,col in enumerate(rows):
        for r in col: adj[r] |= 1<<p
    active = (1<<len(rows))-1
    degree = [a.bit_count() for a in adj]
    base = [0.01*p+.35*len(col) for p,col in enumerate(rows)]
    choices = [0,1]
    static = sorted(choices,key=lambda p:base[p]+min(degree)*sum(1/degree[r] for r in rows[p]),reverse=True)
    assert order_choices(choices,rows,adj,active,min(degree),base) == static
    # Artificial compatible-mask snapshot: row 1 now has p0/p7 while row 2
    # still has p1/p3/p5/p8. Every row retains >= 2 choices, so no forced row
    # preempts the non-forced value-order phase. The score responds to the loss.
    active &= ~(1<<2 | 1<<4)
    current_min = min((active & a).bit_count() for a in adj)
    assert current_min == 2
    assert order_choices(choices,rows,adj,active,current_min,base)[0] == 0
    assert static[0] == 1
    # All tested choices are active and have positive support on their rows.
    assert all(active & (1<<p) for p in choices)
    print("PASS: root-equivalent ranking; residual support changes priority")


if __name__ == "__main__":
    small_asserts()
