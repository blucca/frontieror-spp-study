# FrontierOR SPP — six-case Python research replay

An independent, reproducible study of all six complete public `hoffman1993`
set-partitioning instances. **Frozen Python Main v1** combines a bitset
exact-cover basin probe with warm-started, full-model HiGHS.

## All six official cases, matched versions, seed1

| Case | Python Main v1 | Cold HiGHS1.15.1 | Cold CP-SAT9.15.6755 |
|---|---:|---:|---:|
| tiny | 16 optimal | 16 optimal | 16 optimal |
| large1 | 2833 | 3541 | **1832** |
| large2 (easy) | 229 optimal | 229 optimal | 229 optimal |
| large3 | **240** | 453 | 968 |
| large4 | **331** | no feasible witness | no feasible witness |
| large5 | **180 optimal** | **180 optimal** | no feasible witness |

Main produces a checked whole solution on 6/6 cases. CP-SAT wins large1;
Main has a feasibility advantage on large4; Main and HiGHS tie optimally on
large5. The three missing baseline witnesses are real entry failures after
the fixed search budget, with resource gates passing; they have no cost value.
All 18 planned seed1 benchmark runs completed. Originally held-out inputs
large1/4/5 use the exact pinned public revision and no reference downloads.

## Hard3 paired seeds: large seed sensitivity

| Seed | Python v1 family | Cold HiGHS 1.15.1 | Lower cost |
|---|---:|---:|---|
| 1, original retained run | 240 | 453 | Python v1 |
| 2 | 411 | 440 | Python v1 |
| 3 | 510 | 337 | Cold HiGHS |

Python v1 wins 2 of 3 pairs and loses seed 3. All six hard witnesses pass both
checkers and the resource gate. The original seed-1 entry stays frozen; the
seed-2/3 source only exposes RNG/HiGHS seeds and is archived separately under
[`experiments/paired-seeds/`](experiments/paired-seeds/). Additional Main seed-2 tiny/easy checks retain costs16/229.

**Scope:** all six public cases, paired hard3 seeds 1/2/3, 2 allowed CPUs,
4 GiB address space, 60 s external whole-process limit, at most 55 s internal.
Measurements use Linux/Python 3.13.5; the advertised Main images use Python
3.12/3.14. Solver and NumPy versions match; interpreter and ancillary packages
are documented in [RESULTS.md](RESULTS.md). This is a public research replay;
competition registration and submission count: 0.

## Replay

Verify 22 full-run witnesses and the three recorded no-witness baseline failures,
using Python's standard library, with no solver execution:

```sh
python3 -B verify_replay.py
```

For a new measurement on Linux with Python 3.13 and an existing `uv` executable:

```sh
export PYTHONDONTWRITEBYTECODE=1
python3 -B eligible-baseline/controller.py install --root "$PWD" --uv "$(command -v uv)"
# One serial measured batch, including both original and independent checkers.
python3 -B eligible-baseline/controller.py batch --root "$PWD" \
  --algorithms main highs cpsat --instances tiny large2 large3 --tag replay-v1
# Independent K=2 Base fallback fixture.
python3 -B main/base_contract_check.py
# Same six-run seed extension, retaining seed 1; new output under temp/.
python3 -B experiments/paired-seeds/queue.py
# Remaining originally held-out cases, preserving no-witness outcomes.
python3 -B experiments/holdouts/queue.py
```

The installer reproduces the exact three authorized package pins in
[`requirements.txt`](requirements.txt); all observed private-wheel versions are
in [`requirements-replay.txt`](requirements-replay.txt). A fresh clone is below
the install controller's cumulative 600 MiB file gate. Results from a new run
stay under the ignored `eligible-baseline/{main,highs,cpsat,base-contract}/`;
archived evidence under `results/` stays unchanged.

The standalone Main four-argument entry is:

```sh
mkdir -p temp
eligible-baseline/main-env/bin/python -B main/solve.py \
  --problem hoffman1993 --instance source/hoffman1993-large_instance_3.json \
  --output temp/solution.json --time-limit 60
```

The measured controller supplies the OS resource bounds and external timer.
This direct entry supplies the algorithm's internal deadline and complete schema.

## Read the experiment

- [Method and mathematical scope](METHOD.md)
- [Complete measurements, environment and boundaries](RESULTS.md)
- [Original raw solutions, logs, checkers and state](results/2026-11-21/)
- [Remaining public cases and full negative baseline records](experiments/holdouts/README.md)
- [Fixed-pool OSS probe negatives](experiments/restricted-pool/README.md)
- [Isolated dynamic-scarcity probe, separate from Main](experiments/dynamic-scarcity/README.md)
- [Paired hard seeds and their exact source change](experiments/paired-seeds/README.md)
- [Historical C++ / version-mismatched controls and negative experiments](controls/README.md)
- [Data attribution, licensing and modifications](ATTRIBUTION.md)

Original data, schemas and checker:
[FrontierOR audited public release](https://huggingface.co/datasets/frontieror/FrontierOR),
**CC BY 4.0**, credit Minwei Kong and the other FrontierOR authors.
New independent code: MIT. Full stable source receipts: [source/manifest.json](source/manifest.json).
Published Gurobi references are isolated under `evaluation/reference/` for evaluation.
