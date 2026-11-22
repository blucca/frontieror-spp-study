# Complete cold SCIP control — 2026-11-22

**Seven fixed seed1 runs, seven full checked witnesses.** The already installed
OR-Tools9.15.6755 backend supplies SCIP10.0.0 / SoPlex8.0.0. This plain adapter
retains the complete original Boolean model and independently checked results.
The frozen Main v3 entry and all earlier control matrices remain unchanged.

SCIP improves large1 from v3 cost1334 to657 (50.75%) and returns native full
witnesses on dense large4/5. On large3, v3 cost240 and cold HiGHS453 both beat
SCIP567. Keep SCIP and v3 as measured complementary choices; further
self-clique/cache development and this control expansion stop here.

## Complete measured results

Cost is recomputed from the full original binary witness. Whole time includes
the worker and both full checkers. All seven exits are0, with independent exact
and original NumPy2.5.3 checker verdicts **PASS / PASS**.

| Case | Cost | Native bound | SCIP printed gap % | Own wall s | Whole + checkers s | CPU s | RSS MiB | Native status |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| BaseK2 | 2 | 2.000000 | 0.00 | 0.123547 | 0.318896 | 0.319563 | 47.781 | OPTIMAL |
| tiny | 16 | 16.000000 | 0.00 | 0.087366 | 0.267728 | 0.299405 | 48.027 | OPTIMAL |
| large2 | 229 | 229.000000 | 0.00 | 0.259421 | 0.518720 | 0.554676 | 95.742 | OPTIMAL |
| large1 | 657 | 15.339402 | 4183.09 | 56.059815 | 56.440169 | 111.075199 | 671.070 | FEASIBLE |
| large3 | 567 | 55.954042 | 913.33 | 55.393188 | 55.731249 | 110.422139 | 595.234 | FEASIBLE |
| large4 | 331 | 22.876160 | 1346.92 | 57.046242 | 57.414596 | 112.029191 | 862.457 | FEASIBLE |
| large5 | 180 | 11.603205 | 1451.30 | 57.831366 | 58.276609 | 112.789788 | 1045.430 | FEASIBLE |

Total whole229.176360s / CPU448.138671s; maximum RSS1070520KiB;
slowest complete run58.276609s. [Unrounded comparison](comparison.json)
retains native status/objective/bound, both gap definitions, full dimensions,
resources, input hashes and links to every saved run.

**Gap conventions:** the table retains the percentage printed by SCIP in its
complete native stdout. The separately labeled API-derived ratio is
`abs(primal - bound) / abs(primal)`. SCIP uses its own printed convention.
large5 cost180 has native status FEASIBLE and bound11.603205; the earlier
cold HiGHS180 record retains its Optimal status.

## Reused seed1 controls — saved records, zero reruns

| Case | SCIP | Frozen v3 | Cold HiGHS1.15.1 | Cold CP-SAT9.15.6755 |
|---|---:|---:|---:|---:|
| tiny | 16 | 16 | 16 | 16 |
| large1 | 657 | 1334 | 3541 | 1832 |
| large2 | 229 | 229 | 229 | 229 |
| large3 | 567 | 240 | 453 | 968 |
| large4 | 331 | 331 | no whole witness | no whole witness |
| large5 | 180 | 180 | 180 | no whole witness |

[Retained control links and hashes](reused-controls.json) cover the18 original
saved default-seed records. The six original SCIP cases sum to whole228.649s /
CPU447.170s, versus saved v3 whole222.583s / CPU306.335s. This SCIP request2
control uses more measured CPU. The comparison applies to these six original
seed1 cases within the resource envelope below; extra seeds, parameter sweeps,
new cases and old solver reruns are0.

## Model, cold entry and resource contract

- Full original costs, all M Boolean variables, every N equality `Ax=1`, and
  every active Base bound row; K is `num_constraints`. The original BaseK2
  fixture has `num_bases=1`, K2, actual model3rows, selected `[1]`, cost2.
- Tiny has30rows/25columns/132nnz. Each large case has100rows/15000columns;
  coverage nnz187822/17816/67522/323670/516521 for large1/2/3/4/5.
  Saved native values are exactly binary across all seven complete witnesses.
- [scip_baseline.py](scip_baseline.py) reads the original instance cold:
  hints, references, hard-coded answers, alternate-solver witnesses and deadline
  fallback are0. Seed is `randomization/randomseedshift=1`.
- [original_v3.py](original_v3.py) is the unchanged product source. The adapter
  uses its stdlib input/dimensions/exact-cover/cost/output helpers. highspy and
  NumPy are absent from the SCIP worker; the original NumPy checker runs in a
  separate process. Capability attribution belongs to SCIP; this study adds
  the plain adapter and matched complete measurement/checking.
- Two allocated CPUs, recorded affinity `[0,1]`, 4GiB address-space limit,
  RLIMIT_CPU120s per process, complete worker/checkers deadline60s. Every SCIP
  `SetNumThreads(2)` call returns true. This records the request and setter
  receipt; actual native worker count remains unreported.
- Internal requested budget55s includes import/build. Remaining native time
  requests are54.481–54.766s. Four large native searches measure55.020–56.580s,
  native `WallTime` reaches56.797s, and own wall reaches57.831s. The measured
  native soft-limit overrun is retained; all complete runs finish before60s.
- Fixed serial order: BaseK2, tiny, large2, large1, large3, large4, large5;
  independent queue timeout900s and total native CPU budget900s. The first
  three full checks pass before the four remaining cases. This actual queue
  records0 negative runs; setup/checker errors stop the queue, while native
  negative/resource outcomes retain their real failed records.

## Replay from the repository root

Use the existing matched environment from the root [replay instructions](../../README.md#replay).
The original controller snapshot
[`versions/v3/recorded_controller.py`](../../versions/v3/recorded_controller.py)
is byte-identical to the measured checker controller. Its legacy selector is
`--algorithm main`; `--script` selects SCIP and the metrics identify SCIP.
This example supplies the measured whole-process limits, including both
checkers. Set `CPU_PAIR` to two allowed CPUs (`0,1` in the saved runs).

```sh
CPU_PAIR=0,1
mkdir -p temp/scip-replay
(
  ulimit -v 4194304
  ulimit -t 120
  timeout --signal=KILL 60s taskset -c "$CPU_PAIR" \
    python3 -B versions/v3/recorded_controller.py run \
    --root "$PWD" --algorithm main --seed 1 \
    --script "$PWD/research/scip-cold-control-20261122/scip_baseline.py" \
    --instance "$PWD/source/hoffman1993-large_instance_1.json" \
    --out "$PWD/temp/scip-replay/large1"
)
```

The standalone entry also accepts `--problem hoffman1993 --instance <original.json>
--output <solution.json> --time-limit 60 --seed 1`; supply the same external
limits and full checkers for a matched complete replay. BaseK2 reuses
[`versions/v3/base-contract-fixture.json`](../../versions/v3/base-contract-fixture.json).
Six original instance files remain in [`source/`](../../source/).

## Complete receipts and attribution

- [All seven result directories](results/): unchanged `raw-run.json`, normalized
  `run.json`, native stdout/stderr, raw all-M values, full solutions, independent
  exact checks, original NumPy verdicts and checker/worker logs.
- [Source/input hashes and provenance](provenance.json).
- [Original data attribution and CC BY4.0](../../ATTRIBUTION.md): FrontierOR
  authors, including Minwei Kong, audited derivative of
  [frontieror/FrontierOR](https://huggingface.co/datasets/frontieror/FrontierOR).
  Instances are reused in place; this append copies no input datasets.
- Independent adapter/software: [MIT](../../LICENSE).
