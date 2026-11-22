# FrontierOR SPP — deadline-bounded Python Main v3

Independent research replay of all six complete public `hoffman1993` instances.
The current frozen entry adds input-derived large-hole exact-cover repair and
a measured whole-process deadline fallback to the original Python basin method.
**All nine v3 acceptance runs pass**: six default-seed cases, BaseK2 fixture,
and hard3 seeds2/3. Original strong OSS baselines are reused, not rerun.
**Hard3 seed3 remains a loss: Main416 versus cold HiGHS337.**
At default seed1, all six Main outputs are valid: three cases improve cost or
feasibility over the stronger observed cold OSS result, three have equal cost.

## All six cases, default seed1

| Case | Main v3 | Cold HiGHS1.15.1 | Cold CP-SAT9.15.6755 |
|---|---:|---:|---:|
| tiny | 16 optimal | 16 optimal | 16 optimal |
| large1 | 1334 feasible | 3541 | 1832 |
| large2 | 229 optimal | 229 optimal | 229 optimal |
| large3 | 240 feasible | 453 | 968 |
| large4 | 331 feasible | no feasible witness | no feasible witness |
| large5 | 180 feasible | 180 optimal | no feasible witness |

Main provides a checked whole cover on6/6. large1 improves from original v1
2833 to1334, versus the stronger cold CP-SAT1832. large4 retains cost331 when
the native backend is still pending at the Main deadline; both cold baselines
have no whole feasible witness. large5 Main180 is feasible; the retained cold
HiGHS180 is optimal. Failed baseline costs remain absent, never zero.

## Additional complete LS-only control

An explicit OR-Tools9.15.6755 LS-only family control now covers the same nine
runs: seven full checked witnesses and two genuine `UNKNOWN` outcomes. It
uses two FJ first-solution workers followed by interleaved `ls`/`ls_lin`; the
small cases finish in presolve. large1 costs2428, hard3 seeds1/2/3
cost1493/1562/1489, and large4/5 produce no whole witness. Frozen v3 remains
the current entry. [Full results and runnable control](experiments/feasibility-jump/README.md).

The [complete cold SCIP control](research/scip-cold-control-20261122/README.md)
passes all six original seed1 cases plus BaseK2. SCIP large1 costs657 versus
v31334; large3 costs567 versus v3240; the other four original costs tie v3.
All seven return real native full witnesses within60s including both checkers.
SCIP and v3 remain measured complementary choices; the default entry is unchanged.

## Hard3 paired seeds: keep the losing seed

| Hard3 seed | Main v3 | Retained Main v1 | Cold HiGHS1.15.1 |
|---|---:|---:|---:|
| 1 | 240 | 240 | 453 |
| 2 | 350 | 411 | 440 |
| 3 | 416 | 510 | 337 |

v3 wins two of three pairs against cold HiGHS and loses seed3. These are three
fixed seeds on one case, not a population-level performance estimate.

## Deadline behavior

The entry uses existing `Highs.startSolve()/wait()` daemon APIs. If native solve
is pending at the absolute deadline, Main writes only its previously exact-
checked incumbent, closes the complete all-M JSON, flushes logs and exits0.
Metadata states `MAIN_DEADLINE_FALLBACK`, `native_result_available=false`,
`force_exit=true`. No live native solution/info is read in that branch; no prior
whole cover leads to exit2. The large4 full run exits in55.098s algorithm /
55.455s including both checkers. v2/v2.1 previously exceeded60s on that case
and remain [rejected candidate archives](versions/README.md).

## Replay

```sh
# Recompute archived complete witnesses and inspect real failed/timeout records.
python3 -B verify_replay.py

# Linux / Python3.13, existing uv; exact core wheel pins, outside solve timing.
python3 -B eligible-baseline/controller.py install --root "$PWD" --uv "$(command -v uv)"
# Same serial nine-run v3 gate; new outputs under ignored temp/v3/.
python3 -B versions/v3/queue.py

# Standalone Main's four required arguments; optional --seed defaults to1.
mkdir -p temp
eligible-baseline/main-env/bin/python -B main/solve.py \
  --problem hoffman1993 --instance source/hoffman1993-large_instance_3.json \
  --output temp/solution.json --time-limit 60
```

The measured queue supplies2-CPU affinity /4GiB AS and a60s external timer;
Main uses at most55s internal. Measured host: Python3.13.5, Linux x86_64.
Advertised Main images: Python3.12/3.14. Core versions match; ancillary and
resource-envelope differences are recorded in [RESULTS.md](RESULTS.md).

Single-entry archive: [artifacts/frontieror-spp-main-v3.zip](artifacts/frontieror-spp-main-v3.zip),
containing only `hoffman1993/solve.py`; source matches the accepted v3.
This is an independent public research release; formal submission/registration
actions and spending:0.

## Evidence and scope

- [Mechanism and deadline semantics](METHOD.md)
- [LP certificates and dual-guided repair: negative gate result (2026-11-22)](research/lp-dual-certificate-20261122/README.md)
- [Complete cold SCIP third control: seven full witnesses and resource trade-offs (2026-11-22)](research/scip-cold-control-20261122/README.md)
- [Unrounded runs, reused baselines, negative boundaries](RESULTS.md)
- [All nine v3 raw records](results/2026-11-21/v3/)
- [v1 snapshot and rejected v2/v2.1](versions/README.md)
- [Small/global-hole probe records](experiments/large-hole-lns/)
- [Known upstream time-limit reports and measured workaround](experiments/native-time-limit/README.md)
- [Small evaluation-only synchronous soft-limit repro](evaluation/SOFT_LIMIT_REPRO.md)
- [Data attribution, licensing and source receipts](ATTRIBUTION.md)

Full public data and original checker: FrontierOR authors, including Minwei Kong,
[audited FrontierOR release](https://huggingface.co/datasets/frontieror/FrontierOR),
CC BY4.0; original PDFs are outside this replay. Independent software: MIT.
References and observed baseline-cover analyses are evaluation-only materials.

## Bring a real bottleneck

Open an issue with a shareable instance and your current bottleneck. For a whole
engineering engagement, include the scope, acceptance criteria and budget.
