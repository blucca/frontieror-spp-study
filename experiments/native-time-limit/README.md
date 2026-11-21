# Measured native time-limit boundary

Existing upstream #3314/#3606 were open at the2026-11-21 lookup; no new issue,
comment or core fix was sent. Original triage is retained as historical context.
It describes a short presolve-off experiment; the later full v2.1 queue still
exceeded60s, so that candidate is rejected. v3 restores normal presolve.

The actual v3 remedy uses already-installed startSolve/wait daemon APIs with
the entry's absolute deadline. A pending native task yields only the previously
validated whole incumbent and explicit pending-native metadata, followed by
closed/flushed output and process exit. It does not consume a live native result.

Large4 full gate:331,algorithm55.098s/whole55.455s,exit0,both checkersPASS.
Separate12s diagnostic:331,algorithm12.060s/whole12.408s,exit0,both checkersPASS.
The diagnostic source changes the internal-budget constant only; source/raw
records are under `v3/` here and `results/2026-11-21/v3/diagnostic-large4/`.
The local delayed-backend tiny fixture is also retained; it executes no solver.
