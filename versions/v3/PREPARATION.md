# Local release preparation

The candidate uses the existing `Highs.startSolve()/wait()` daemon API with an
absolute entry deadline. Native overrun returns only a previously exact-checked
input-derived incumbent: complete output closed/flushed, then process exit0.
A missing prior whole cover exits2. Live native solution/info is not read while
its worker is pending. Metadata explicitly marks MAIN_DEADLINE_FALLBACK,
native_result_available=false and force_exit=true.

A large4 12s internal diagnostic passed331/exit0/fullM/both checkers in
12.060s algorithm /12.408s complete measured wall; delayed-backend tiny16/all25
local simulation also passed. This checkpoint waits for all9 complete v3 runs
before the public entry is promoted. No native computation is started here.
