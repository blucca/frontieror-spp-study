# Owner-group primary proof, stock fixed-D cost

## Complete primary search

Old partition I gives each leg an owner group. `repair.py` reads all M columns.
State (U,C) holds removed groups and legs covered by selected nonold rotations;
W(U) is every leg of U, T(j) the owners touched by j.

Start U=F intersect I, C empty. Choose a missing leg with fewest legal
candidates; enumerate all original nonold columns covering it. Require j
outside F, rows(j) disjoint from C, T(j) disjoint from pinned groups, and
|U union T(j)|<=k. Union-update U/C; newly touched groups expose **all** their
legs. Terminate at C=W(U), retaining old I\U plus the new columns.

C contained in W(U), disjoint new columns and untouched old groups give
full Ax=1/F/P. Each step covers a new leg; depth <=N. For any feasible J*,
its new columns exactly cover W(I\J*). Each missing leg has one such column,
disjoint from previous choices and touching only removed groups of J*. At
k>=|I\J*| this branch survives. Enumeration therefore reaches a witness,
including expansion beyond initially banned groups.

## Proof and stage statuses

Budgets rise from |F intersect I| to |I|-|P|. Completely failing k proves
D>=k+1; the first witness proves minimum D. Clear failed-state caches each
budget; cache only complete failures. Deadline interruption keeps the last
proven bound and marks the current budget unexhausted. Exhausting all budgets:
INFEASIBLE; interruption without witness: UNKNOWN; conflicting F/P: INFEASIBLE.

`method.py` sends its own complete primary witness to shared stock CP-SAT in
`controls.py`. The all-M cost model retains Ax=1/F/P and fixes
`sum(old x)=|I|-D`. Primary custom status/bound and secondary native status/bound
are separate; `lexicographic_complete` requires both proofs. Interrupted cost
search retains the better checked witness and primary certificate.

Stock CP-SAT/SCIP controls solve full primary, then fix D after native OPTIMAL.
Legal old-one values provide partial hints; pins are constraints. SCIP uses
a fresh instance per objective. v3 supplies unchanged input/witness helpers.

Review checks budget caches, exposed legs, pins and deadlines. All witnesses
receive full-vector/Ax=1/F/P/D/cost and original FrontierOR checks; proofs and
whole/resource success are separate.
