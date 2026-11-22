# LP certificates and dual-guided exact cover — negative result

2026-11-22. **Stop this experimental method; frozen Main v3 remains the default.**
The complete LP certificate works on tiny and the easy `large2` case. The four
other complete LPs remain fractional. Adding dual-guided repair to hard3 yields
costs **240 / 350 / 405**, against retained v3 **240 / 350 / 416**: the three-run
sum falls **1.09344%**, below the preselected 5% gate. These three fixed seeds
on one case are the scope of this comparison.

## Question and stopping rule

Can an all-column LP produce a checked integer optimality certificate on dense
`large4` or `large5`, avoiding the long integer solve? If its cover is fractional,
can integer row prices and reduced-cost lower bounds improve hard3's complete
cold pipeline?

Continue only after either a dense-case whole optimal certificate with a clear
whole-time saving, or at least two of the three hard3 pairs improving cost by
5% each **and** their total cost improving by 5%. Both routes failed. The new
whole-method gate covers tiny, BaseK2 and hard3 seeds 1/2/3 (five runs); the six
LP diagnostics are a separate gate. The stopping decision closes this candidate before
any six-case whole-method expansion. Existing v3 and strong baseline records remain
at their original paths and bytes.

## Six complete LP diagnostics

Every LP uses all original columns and rows, positive Python-int costs, K0 and
0/1 exact-cover incidence. Nonempty columns have a redundant upper bound of 1,
so the LP uses only `x >= 0`; none of these six inputs has empty columns. Native
HiGHS returned LP `Optimal` on 6/6. Every stored integer dual is independently
valid over **all 75,025 original columns**. A complete integer witness plus the
exact dual bound certifies the full integer problem on tiny and `large2` only.

| Case | LP objective | Exact integer lower bound | Rounded whole cover / certificate | External LP process s |
|---|---:|---:|---|---:|
| tiny | 16.000000 | 16 | cost 16, whole Optimal | 0.164222 |
| large2 (easy) | 229.000000 | 229 | cost 229, whole Optimal | 0.214739 |
| large1 | 11.746286 | 12 | fractional; rounded cover fails | 0.365165 |
| large3 | 53.181713 | 54 | fractional; rounded cover fails | 0.318094 |
| large4 | 11.636969 | 12 | fractional; rounded cover fails | 0.465501 |
| large5 | 6.578892 | 7 | fractional; rounded cover fails | 0.716401 |

The serial six-process diagnostic queue takes **2.259654s**, CPU 2.524022 s,
maximum RSS 128,296 KiB. Each [raw LP report](results/lp/) separately retains its
build/native/complete time, full primal vector, floating row duals, integer
prices, all scaled reduced costs and numerical LP status. [LP summary](results/lp-summary.json)
retains external process times and queue timing. These are LP diagnostics;
complete method/checker time is measured below.

## Complete method gate: all five outputs pass

The executed wrapper keeps original independent cold search, the density basin
and original large-hole repair. It adds a full LP and up to 6 s of integer-dual
large-hole repair, then gives the remaining absolute 55 s budget to the original
full warm HiGHS model. It preserves the prior exact incumbent and original
native-deadline exit contract. BaseK2 delegates to frozen v3.

| Case / seed | New cost | Retained v3 | Retained cold HiGHS 1.15.1 | New whole s, including collected checks |
|---|---:|---:|---:|---:|
| tiny / 1 | 16 | 16 | 16 | 0.267552 |
| BaseK2 / 1 | 2 | 2 | — | 0.267744 |
| hard3 / 1 | 240 | 240 | 453 | 55.255483 |
| hard3 / 2 | 350 | 350 | 440 | 55.270102 |
| hard3 / 3 | 405 | 416 | 337 | 55.301548 |

All five recorded outputs pass the original solution contract, original
NumPy feasibility checking and the independent full-M/exact-cover/Base check.
[Complete run, solution, checker and metric records](results/method/) are retained.
The hard3 sum is **1006 -> 995**; seed 1/2 have zero cost improvement, seed 3 has
**2.64423%** paired whole-run improvement. Seed3 still costs more than the
retained cold HiGHS 337 result. Maximum method RSS is 673,188 KiB.

Within the new seed 3 run, original large-hole repair first reaches 419; its
subsequent dual stage reaches 405. That **419 -> 405** is an observed within-run
stage improvement. The retained-v3 **416 -> 405** difference of 11 belongs to
this complete new run, which also changes LP startup and remaining stage time.
The paired delta covers the full wrapper, including LP startup and the
reallocated remaining runtime; the 419 -> 405 event is the within-run dual repair.
See [full contrast and traces](results/final-contrast.json) and [gate summary](results/summary.json).

## Exact certificate and source correction

For positive integer costs, integer row prices `P` and positive integer scale
`S`, check every original column `j`:

```text
sum(P[r] for r in column[j]) <= cost[j] * S
L = sum(P) / S
integer optimum >= ceil(L)
```

Each feasible exact cover uses every row once. Summing these column inequalities
therefore proves the full-problem lower bound. A full exact-cover witness whose
integer cost equals `ceil(L)` proves optimality. Negative row prices are valid;
Python's integer ceiling handles their sign exactly. Floating LP duals only
choose candidate integer prices. A uniform downward correction and the final
all-column integer inequalities establish the certificate.

- [`dual_lp.py`](dual_lp.py) is the reviewed, strict-positive-Python-int version.
- [`lp-executed-v1.py`](lp-executed-v1.py) preserves the exact first-six-LP source.
  It previously accepted integer-valued floats; that domain was subsequently
  tightened. All six archived inputs already have positive Python-int costs;
  the six reports were retained after the domain correction, without rerunning.
- The float guard addresses an actual tiny counterexample: costs
  `[1e16, 1, 10**16]` can make floating `v3.cost` lose one integer unit, turning
  a more expensive witness into a false equal-bound candidate. The strict
  certificate path rejects float costs, including integer-valued floats.
- [`original_v3.py`](original_v3.py) is byte-identical to frozen
  [`main/solve.py`](../../main/solve.py). [`method.py`](method.py) and
  [`dual_search.py`](dual_search.py) are the actual executed method sources.
  `dual_pool` is an auxiliary checked helper; the executed wrapper uses the
  original canonical columns rather than that pool helper.
- [Source versions and provenance](provenance.json) distinguish executed and
  corrected source. Raw historical `/data/workspace/...` locations remain in
  the unchanged run records; the commands below use clone-local paths.

## Recheck the stored evidence — standard library only

From this repository root, on Linux with Python 3:

```sh
python3 -B research/lp-dual-certificate-20261122/dual-review-assert.py
python3 -B research/lp-dual-certificate-20261122/dual-search-oracle.py
python3 -B research/lp-dual-certificate-20261122/check_archived.py
```

The first check enumerates 21 tiny price/scale cases, signed/rounded bounds and
the float-domain counterexample. The second checks 12 target/seed combinations,
forced reduced-cost increments, partial/global strict repair, incumbent and
deadline retention. The last rechecks all six archived full-column certificates
and five full binary witnesses, and reads their saved official checker receipts.
These checks invoke no numerical solver. Original NumPy/schema receipts are
retained from the measured five-run gate.

## Plain reproduction commands

Run from the repository root on Linux. Choose an **already installed** Python
with highspy 1.15.1 and NumPy 2.5.3; measured Python was 3.13.5. The commands
regenerate LP reports or whole solutions/algorithm metrics under ignored `temp/`.
Two-CPU affinity, 4 GiB virtual-address limit and 60 s outer timer match the recorded
envelope; method's internal budget is at most 55 s. Native LP wait is at most 5 s
in the diagnostic and 2 s in the complete wrapper. Solver/control installation
and private queue/controller orchestration are outside this study.

```sh
PYTHON=python3                 # select your existing pinned interpreter
STUDY=research/lp-dual-certificate-20261122
OUT=temp/lp-dual-certificate-20261122
"$PYTHON" -B -c 'import highspy, numpy; assert highspy.Highs().version() == "1.15.1"; assert numpy.__version__ == "2.5.3"'
mkdir -p "$OUT/lp"
for stem in tiny_instance large_instance_2 large_instance_1 large_instance_3 large_instance_4 large_instance_5; do
  mkdir -p "$OUT/lp/$stem"
  timeout 60 "$PYTHON" -B "$STUDY/dual_lp.py" \
    --instance "source/hoffman1993-$stem.json" \
    --output "$OUT/lp/$stem/report.json" --lp-seconds 5 \
    > "$OUT/lp/$stem/stdout.log" 2> "$OUT/lp/$stem/stderr.log"
done
```

```sh
# Same PYTHON, STUDY and OUT; no baseline reruns.
CPUS=$("$PYTHON" -B -c 'import os; print(",".join(map(str, sorted(os.sched_getaffinity(0))[:2])))')
for case in tiny base-k2; do
  if [ "$case" = tiny ]; then INPUT=source/hoffman1993-tiny_instance.json
  else INPUT=main/base-contract-fixture.json; fi
  mkdir -p "$OUT/method/seed1/$case"
  (ulimit -v 4194304; timeout 60 taskset -c "$CPUS" "$PYTHON" -B "$STUDY/method.py" \
    --problem hoffman1993 --instance "$INPUT" \
    --output "$OUT/method/seed1/$case/solution.json" --time-limit 60 --seed 1) \
    > "$OUT/method/seed1/$case/algorithm.stdout.log" 2> "$OUT/method/seed1/$case/algorithm.stderr.log"
done
for seed in 1 2 3; do
  mkdir -p "$OUT/method/seed$seed/large3"
  (ulimit -v 4194304; timeout 60 taskset -c "$CPUS" "$PYTHON" -B "$STUDY/method.py" \
    --problem hoffman1993 --instance source/hoffman1993-large_instance_3.json \
    --output "$OUT/method/seed$seed/large3/solution.json" --time-limit 60 --seed "$seed") \
    > "$OUT/method/seed$seed/large3/algorithm.stdout.log" 2> "$OUT/method/seed$seed/large3/algorithm.stderr.log"
done
```

## Attribution and boundaries

Data, schemas and original checker reuse the existing complete [`source/`](../../source/)
artifacts; this directory contains **zero copied input instances**. Credit
Minwei Kong and the FrontierOR authors; original `hoffman1993` task attribution
is Hoffman & Padberg (1993), *Solving Airline Crew Scheduling Problems by
Branch-and-Cut*. [Full source/provenance](../../ATTRIBUTION.md) and dataset-card
snapshot `ef42a2eac13595453f986d9df0b62e86e75ab596` apply. Independent software
is [MIT](../../LICENSE); research text, metrics and generated solution witnesses
retain CC BY 4.0 as described in the repository attribution map.

The certified fast path covers positive Python-int costs / K0; the full wrapper
uses its original Base backend outside that domain. All six LP diagnostics and
the five complete method runs are reported separately. This frozen negative
experiment changes no default entry, old results or measured baseline.
