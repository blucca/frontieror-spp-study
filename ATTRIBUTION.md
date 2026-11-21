# Attribution and license map

This is an independent research replay by **blucca**, using an audited derivative
of the **FrontierOR benchmark**. Credit **Minwei Kong and the other FrontierOR
authors**, as identified by the dataset card, and the upstream
[SmartOR/FrontierOR dataset](https://huggingface.co/datasets/SmartOR/FrontierOR).
The downloaded audited release is
[frontieror/FrontierOR](https://huggingface.co/datasets/frontieror/FrontierOR),
dataset-card commit `ef42a2eac13595453f986d9df0b62e86e75ab596`, retrieved
2026-11-21. The original card and license declaration are retained in
[`source/README.md`](source/README.md) and [`source/LICENSE.md`](source/LICENSE.md).

The `hoffman1993` task cites Hoffman & Padberg (1993),
*Solving Airline Crew Scheduling Problems by Branch-and-Cut*,
Management Science 39(6):657–682. The paper's PDF is outside this replay.

| Material | License |
|---|---|
| New independent solver, baseline adapters, helpers and replay code | [MIT](LICENSE) |
| `source/`, including original instances, schemas and checker | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| `evaluation/reference/`, including original Gurobi code and results | CC BY 4.0 |
| Original research text, metrics and generated solution witnesses | CC BY 4.0 |

CC BY 4.0 [legal code](https://creativecommons.org/licenses/by/4.0/legalcode).
The repository-wide MIT software license preserves the CC BY 4.0 terms on
the attributed benchmark artifacts.

## Changes and provenance

- Copied all six **complete** public instance JSONs, two schemas, the original
  NumPy checker, dataset card and source license **without byte changes**.
  Filenames receive a `hoffman1993-` prefix for a task-local replay layout.
- Copied two published reference-solution JSONs and the original Gurobi/model
  logger code without byte changes into the separate evaluation directory.
- Authored independent Python and historical C++ implementations, exact
  witness checker, sparse transport, experiment notes and result tables.
- Exposed fixed seeds in a separate v1-family source; retained the original
  frozen Main byte content and published the source diff. Adapted only the
  paired queue filesystem paths for a clone-local, temp-output replay.
- Generated full-M binary solution witnesses and measured runtime logs.
  Historical absolute `/data/workspace/...` paths in raw records are retained.
- Normalized download receipts into [`source/manifest.json`](source/manifest.json):
  stable public URLs, retrieval time, commit where available, ETag, byte length
  and SHA-256 are preserved; transient signed CDN redirect URLs are omitted.
- Adapted the exploratory entropy script's CLI/file layout; its uniform-random
  hyperedge calculation is a heuristic, with original observation JSON retained.

The solver reads only its explicit instance argument. Published Gurobi solutions
were used for evaluation and were absent from the cold-run source directory.
The recorded source inventory is in
[`results/2026-11-21/runtime/initial-host-environment.json`](results/2026-11-21/runtime/initial-host-environment.json).

## Remaining official cases

large1/4/5 were retrieved on2026-11-21 from the cached exact official instance
links at pinned revision `ef42a2eac13595453f986d9df0b62e86e75ab596`.
The complete bytes are unchanged, source receipt records are retained in
`source/holdout-source-receipts.json`, and file hashes/URLs join the source
manifest. Additional reference downloads:0. The originally held-out replay
queue adapts only public clone paths/output paths and allowed CPU IDs;
the original measured queue is retained as an audit artifact. The isolated
dynamic probe source changes only compatible-support value ordering and is
separate from frozen Main and its full-run scores.
