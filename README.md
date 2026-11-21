# FrontierOR SPP — Python research replay

An independent, reproducible study of three complete public `hoffman1993`
set-partitioning instances. **Frozen Python Main v1** combines a bitset
exact-cover basin probe with warm-started, full-model HiGHS.

The hard-instance paired seed experiment shows **large seed sensitivity**:

| Seed | Python v1 family | Cold HiGHS 1.15.1 | Lower cost |
|---|---:|---:|---|
| 1, original retained run | 240 | 453 | Python v1 |
| 2 | 411 | 440 | Python v1 |
| 3 | 510 | 337 | Cold HiGHS |

Python v1 wins 2 of 3 pairs and loses seed 3. All six hard witnesses pass both
checkers and the resource gate. The original seed-1 entry stays frozen; the
seed-2/3 source only exposes RNG/HiGHS seeds and is archived separately under
[`experiments/paired-seeds/`](experiments/paired-seeds/). The original three-case
matched-version results are:

| Seed-1 Python run | tiny | easy `large2` | hard `large3` |
|---|---:|---:|---:|
| Main v1 | 16 | 229 | 240 |
| HiGHS 1.15.1, cold | 16 | 229 | 453 |
| CP-SAT 9.15.6755, cold | 16 | 229 | 968 |

All nine original runs pass complete-schema, independent exact, original NumPy
and resource checks. Additional Main seed-2 tiny/easy checks retain costs16/229.

**Scope:** three public cases, paired hard seeds 1/2/3, 2 allowed CPUs,
4 GiB address space, 60 s external whole-process limit, at most 55 s internal.
Measurements use Linux/Python 3.13.5; the advertised Main images use Python
3.12/3.14. Solver and NumPy versions match; interpreter and ancillary packages
are documented in [RESULTS.md](RESULTS.md). This is a public research replay;
competition registration and submission count: 0.

## Replay

Verify all 16 archived complete witnesses (original nine + Base + six seed runs),
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
- [Paired hard seeds and their exact source change](experiments/paired-seeds/README.md)
- [Historical C++ / version-mismatched controls and negative experiments](controls/README.md)
- [Data attribution, licensing and modifications](ATTRIBUTION.md)

Original data, schemas and checker:
[FrontierOR audited public release](https://huggingface.co/datasets/frontieror/FrontierOR),
**CC BY 4.0**, credit Minwei Kong and the other FrontierOR authors.
New independent code: MIT. Full stable source receipts: [source/manifest.json](source/manifest.json).
Published Gurobi references are isolated under `evaluation/reference/` for evaluation.
