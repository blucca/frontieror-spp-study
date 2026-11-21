---
license: cc-by-4.0
language:
  - en
pretty_name: FrontierOR Benchmark
size_categories:
  - n<1K
task_categories:
  - other
tags:
  - operations-research
  - optimization
  - mixed-integer-programming
  - gurobi
  - benchmark
  - llm-for-or
configs:
  - config_name: meta
    data_files: metadata/paper_meta_info.json
---

# FrontierOR Benchmark

<p align="center">
  <a href="https://www.frontieror.org"><img src="https://img.shields.io/badge/%F0%9F%8C%90%20Website-www.frontieror.org-52487b" alt="Website"></a>
  &nbsp;
  <a href="https://arxiv.org/abs/2605.25246"><img src="https://img.shields.io/badge/arXiv-2605.25246-b31b1b?logo=arxiv&logoColor=white" alt="arXiv"></a>
  &nbsp;
  <a href="https://github.com/Minw913/FrontierOR"><img src="https://img.shields.io/badge/GitHub-FrontierOR-24292f?logo=github&logoColor=white" alt="GitHub"></a>
</p>

A benchmark of **180 literature-grounded OR tasks**, each packaged as a
self-contained reproducible unit: natural-language problem description,
mathematical formulation, reference Gurobi implementation, test instances,
reference solutions, and an automated feasibility checker.

Designed for evaluating LLMs on the end-to-end task of turning a research
paper's OR problem into runnable, verifiably-correct optimization code.

## **🎯 FrontierOR-v1 is released!**

**FrontierOR-v1 was updated on 2026-09-27.** This important dataset update consolidates the canonical 180-task collection, Gurobi references, hard-set split metadata, feasibility checkers, and task-instance artifacts. For detailed fixes and compatibility notes, see [`RELEASE_NOTES.md`](RELEASE_NOTES.md).

## Layout

| Path | Purpose |
| --- | --- |
| `README.md` | Dataset overview and loading instructions |
| `RELEASE_NOTES.md` | Detailed FrontierOR-v1 update notes |
| `CASE_IDS.txt` | Canonical task id list |
| `LICENSE.md` | Dataset license |
| `metadata/` | Paper metadata, Gurobi reference summaries, and benchmark split metadata |
| `metadata/paper_meta_info.json` | Metadata for all 180 canonical papers, including optimization direction |
| `metadata/gurobi_references.parquet` / `.csv.gz` | Canonical Gurobi objectives, runtimes, statuses, and related reference fields |
| `metadata/hardset/` | Hard-set ids, ranking inputs, methodology, and reproduction script |
| `tasks/<task_id>/` | Self-contained task package for one paper |

## What's in each task folder

| File / dir | Purpose |
| --- | --- |
| `problem_description.txt` | Natural-language problem statement |
| `mathematical_formulation.md` | Mathematical model (variables, constraints, objective) |
| `gurobi_code.py` | Reference Gurobi implementation |
| `feasibility_check.py` | Automated solution validator |
| `solution_logger.py` | Utility for serializing solutions |
| `instance_schema.json` | JSON schema for input instances |
| `solution_schema.json` | JSON schema for solutions |
| `instance/` | Six benchmark instances: `tiny_instance.json` and `large_instance_1.json` through `large_instance_5.json` |
| `gurobi_solution/` | Reference Gurobi solutions for the tiny and five large instances |
| `gurobi_solution_log/` | Anytime incumbent objective trajectories from the reference Gurobi runs |
| `gurobi_feasi_result/` | Feasibility-check outputs for the reference Gurobi solutions |
| `solverless_models/` | Optional task-local assets for checkers that need solver-independent validation models |

## Loading the metadata

Load the 180-paper metadata table from `metadata/paper_meta_info.json`:

```python
from datasets import load_dataset
meta = load_dataset("frontieror/FrontierOR", "meta", split="train")
print(meta[0])
```

## Downloading and updating the task files

For the per-paper instance / solution data, clone or download the full
repository — the structure is intentionally a file tree, not a flat HF
dataset, because each paper is its own reproducible package under
`tasks/<task_id>/`.

```bash
hf download frontieror/FrontierOR --repo-type dataset --local-dir frontier-or
```

To update an existing local copy, rerun the same command. Unchanged files are
reused, and only missing or changed files are downloaded.

If your local copy was created by `git clone`, update it with:

```bash
cd frontier-or
git pull
git lfs pull
```

When upgrading from an older snapshot, note that files deleted upstream may
remain in an existing `--local-dir` checkout. Remove stale top-level files
manually if present (including the retired `metadata/paper_meta_info_180.csv`),
or refresh from a clean directory when exact directory
parity is required.

<!-- ## License

Released under **CC-BY-4.0**. If you use this benchmark, please cite the
accompanying paper (citation below) and respect the original publishers'
copyright on the source PDFs. -->

<!-- ## Citation

```bibtex
@misc{frontier-or-2026,
  title  = {FrontierOR: A Benchmark for LLM-Based Operations Research Code Generation},
  author = {Kong, Minwei and others},
  year   = {2026},
  url    = {https://huggingface.co/datasets/frontieror/FrontierOR}
}
``` -->
