# Six-second global/large-hole initialization probe

Separate first-stage measurements: large1 seed1 cost1334 from cold2833,
hard3 seed2 cost350 and seed3 cost380. Full-M witnesses and both checker
results are retained in the case directories. These remain probe scores;
the promoted v3 full pipeline's hard3 seed3 result is416.

This pure-Python probe alternates global and75%-100% incumbent-column holes,
at most0.6s each, with strict price-ordered repairs. The preserved small-hole
comparison produced zero improvement on large1.

```sh
mkdir -p temp
python3 -B experiments/large-hole-lns/probe.py --problem hoffman1993 \
  --instance source/hoffman1993-large_instance_1.json \
  --output temp/large-hole-probe.json --time-limit 60 --seed 1
```

The probe has its own six-second initialization cutoff and makes no native
solver call. Original source/diff/raw metrics are local to this archive.
