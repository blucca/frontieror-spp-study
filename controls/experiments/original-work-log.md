# Native DLX + hole-LNS work log

## NOTE 1 — initial implementation (2026-11-21)

- AI workflow authored solver.cpp from input schema/data; human code edits: 0.
- Read schemas, three instance JSONs, source README/LICENSE; source solution JSONs were excluded from all commands and solver inputs.
- Compile: c++ -std=c++17 -O3 -DNDEBUG solver.cpp -o solver, success.
- Minimal self-check: hand-constructed 4-row/6-column toy; exact cover [0,1], cost 4, full-hole optimality certificate. self_check.sh passed.
- Local smoke subprocesses capped at 500 MiB address space. Independent Python check recomputed exact per-row coverage and objective directly from original instances; all three passed. No optimization package used.

| Instance | Limit | Final cost | Cold cost | Cold seconds | Cold nodes | Improvements | End-to-end wall |
|---|---:|---:|---:|---:|---:|---:|---:|
| tiny | 2 s | 16 | 16 | 0.000100 | 6 | 0 | 0.002820 s |
| large2 | 2 s | 229 | 257 | 0.007160 | 68 | 8 | 1.999322 s |
| large3 | 5 s | 345 | 781 | 0.012828 | 45 | 7 | 4.999694 s |

- Measured cumulative maximum child RSS: 10,632 KiB. Tiny B&B exhausted the full-row neighborhood and proved optimality.
- smoke-*.json / .time retain raw metrics; .dat were generated exclusively from original instances.
- First attempted /usr/bin/time measurement failed because this environment has no /usr/bin/time; no solver was executed in that attempt. Replaced measurement with Python subprocess/monotonic/resource and obtained the above results.
- Cold startup is already fast on large3. Next decision will use measured 55-second hard3 outcomes after the baseline agent releases its exclusive remote-heavy slot.

## NOTE 2 — isolated anchor-ejection experiment

- Preserved the initial source/binary as solver-v1.cpp / solver-v1.
- solver-v2.cpp alternates ordinary holes with holes containing all incumbent edges touched by a cheap unselected anchor, then forces the anchor and repairs remaining rows. Other mechanisms were unchanged.
- First v2 compile failed after a code-generation script inserted literal backslash-n tokens; fixed those tokens before executing the test. No failed binary was run.
- Same large3 / seed 1 / 5-second local budget / 500 MiB cap: cost 405, cold cost 781, 9 strict improvements, 74 anchor holes and 5 anchor improvements, 148 total holes, 53 complete holes, 2,934,603 nodes. Exact original-row/objective recomputation passed.
- Initial v1 cost 345 is better in this smoke comparison. Forced anchors moved half the holes to >=50 rows, lowering completed-hole fraction; this experiment is retained for audit, with v1 kept as the main implementation.

## NOTE 3 — isolated dual-ascent bound experiment

- solver-v3.cpp keeps v1 neighborhood selection but strengthens row prices once at each hole root with dual ascent.
- Residual edge cost is c_e - sum(pi_r), with nonnegative residual cost. Node row prices become pi_r + min_active_e(residual_cost_e / |e|). Sum over remaining rows is admissible, and sorted vertical lists retain O(remaining rows) bound computation per node.
- Same large3 / seed 1 / 5-second local budget / 500 MiB cap: cost 345, same selected indices as v1, 7 strict improvements, 192 holes, 105 complete holes, 2,676,834 nodes. Exact original-row/objective recomputation passed.
- Root-bound sums improved from 9,190.63 to 14,568.11 (+58.5%), while total nodes decreased just 0.7% relative to initial v1. The observed objective and throughput gain is small, so the simpler v1 remains main.
- All three version sources, binaries and smoke JSONs remain confined to this method directory. Main source has not incorporated the experimental changes.

## NOTE 4 — formal-run instrumentation

- Main v1 source now emits metrics.improvement_trace as [elapsed_seconds, objective] at cold feasibility and every strict improvement. The solver mechanism is unchanged.
- Recompiled C++17/O3 and reran the one minimal self-check; pass.
- current-source.sha256 identifies the source to compile for formal baseline comparison.
- Baseline agent reports cold HiGHS hard3 seed1 / 55 seconds: cost 296, bound 57, 2.22 GiB RSS, independent exact and original checker PASS. Native formal run is pending the baseline agent's remote-slot release and root scheduling.

## NOTE 5 — authorized v1 formal run preparation

- Root assigned the released Instabox4 slot exclusively to this agent for one cold large3 / seed 1 / 55-second v1 run.
- Frozen current main source as solver-formal-v1.cpp; formal-v1-source.sha256 retains SHA256 73f85abd4bed67ce05779cb6cc41d017e771d05a1b0ea6b55271583f2a524736.
- formal_once.py is a one-run bounded wrapper around the existing shared helper, preserving baseline affinity 0,1 / 4 GiB AS / thread caps 2, 60-second external end-to-end and 55-second solver budget. It records raw JSON, all-M solution, independent exact check, original NumPy checker and OS usage.
- This formal run makes no algorithm changes.

## NOTE 6 — v1 formal large3 outcome, remote slot released

- Source/binary/controller fingerprints, actual remote source inventory and all run outputs are retained under formal-v1/ and formal-v1-remote-receipts.tar.gz.
- Instabox4 same-envelope cold native run: 55-second solver budget, seed 1, CPU affinity 0,1, 4 GiB address-space bound, 60-second external wall gate.
- **PASS**: objective 294; 55.2372867-second external end-to-end including input conversion/full normalization/original checker; 55.195694 user + 0.035543 system CPU seconds; 44,608 KiB max RSS.
- Complete 15,000-variable solution, independent exact checker and original NumPy checker all passed.
- Cold full-pool feasibility: 781 in 0.007450 seconds, 45 nodes.
- Strict improvement trace: 345 at 0.703 s; 322 at 10.897 s; 318 at 16.447 s; 294 at 29.243 s. The last 25.75 seconds retained 294. Total 3,960 holes / 2,449 completed / 10 strict improvements / 50,588,741 nodes.
- Native 294 is 0.676% lower cost than same-envelope HiGHS 296, with one active solver CPU versus the baseline's two allowed solver threads and measured process RSS 43.56 MiB versus 2,273.4 MiB. This is the one authorized seed comparison.
- Root and baseline agent were notified that the remote-heavy task finished and the Instabox4 slot was released. Next authorized experiment is an isolated density-restricted cold probe, motivated by the observed plateau.

## NOTE 7 — density-restricted cold probe and C++ branch STOP

- Root's authorized single-mechanism v4 experiment used only original cost/coverage distribution and row-degree support, with the theorem: an exact partition using only columns of density <= theta has objective <= theta*N.
- density-probe-analysis.json records data-derived support cutoffs after equal-coverage cheapest-column deduplication. For large3, support ceil(2*ln(100))=10 gives theta 1.6 / 439 columns / min degree 12; doubled support 20 gives theta 2.25 / 652 columns / min20; support40 gives theta3.5 / 1112 columns / min41. Tiny full minimum degree1 falls below support7; large2 support10 cutoff density31.667 is higher than its full-cold incumbent density, so both skip these probes.
- First v4 attempt used multiplicative density widening 1.6 -> 2.0 -> 2.5 and 120,000-node cap; each failed by node cap after 0.12-0.14 s. Advancing the shared RNG changed fallback LNS; 5-second final cost413. Source/binary preserved as solver-v4-attempt1.cpp / solver-v4-attempt1; raw smoke-v4-large3.json.
- Revised v4 keeps the original LNS RNG stream separate, widens by actual row-support doubling and lets 450 ms govern search with a 4M node cap. Results on large3 seed1 / 5 s / 500 MiB local cap:

| theta | columns | min degree | nodes | probe wall | result |
|---:|---:|---:|---:|---:|---|
| 1.6 | 439 | 12 | 395,521 | 0.450141 s | time abort, no cover found |
| 2.25 | 652 | 20 | 438,401 | 0.450085 s | time abort, no cover found |
| 3.5 | 1,112 | 41 | 497,025 | 0.450153 s | time abort, no cover found |

- All three searches were interrupted by time; no cheap-pool infeasibility certificate was produced. Full-pool cold incumbent781 was preserved, then ordinary v1 LNS returned the same cost345 / selected indices as the initial v1 5-second smoke. Original exact-row and cost recomputation passed.
- v4 remains an isolated experiment; main solver.cpp and the formal-v1 control are unchanged.
- Root established the target Main runtime as Python-only and reassigned the main budget to the Python agent. **C++ branch STOP** after this authorized smoke; no further C++ product work or remote-heavy run. Native source/control receipts remain for the self-hosted/native runtime scope.
- Sent the Python agent the data-derived thresholds, min-compatible-row branching, seed-stable ratio perturbation, cost-sharing bound, exact-cover theta*N proof, bitset-active/conflict update translation, and timeout measurements. Main Python refinement and runtime-mirror baselines continue under that agent.
- Human code edits across this C++ branch: 0. Reference solutions as algorithm inputs: 0.
