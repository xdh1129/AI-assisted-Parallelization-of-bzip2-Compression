# lbzip2 optimization stage (`feat/lbzip2-optimize`)

A second parallel-bzip2 "version" for this project: instead of our hand-written
OpenMP `pbzx`, we vendor the mature **lbzip2** (https://github.com/kjn/lbzip2),
profile it, and attempt to improve it — benchmarked with the **same harness**
used for every other version (`bench/run_bench.py`, `bench/verify.py`).

## Layout

- `lbzip2/` — vendored editable fork of upstream lbzip2 (see `VENDORED_FROM.txt`).
  Build trees `lbzip2/build*/` are gitignored.
- `bench/lbzip2_pbzx.sh` — **adapter**: exposes the pbzx CLI
  (`-i/-o/--threads/--block-size/--level`) on top of lbzip2 and emits the
  `PBZX_STATS` line the harness parses, so `run_bench.py`/`verify.py` drive
  lbzip2 unchanged. ⚠️ lbzip2 reads `$LBZIP2`/`$BZIP2`/`$BZIP` as CLI options;
  the adapter selects the binary via **`LBZIP2_BIN`** and unsets those.

## Build

```bash
cmake -S lbzip2 -B lbzip2/build -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_C_FLAGS_RELEASE="" -DCMAKE_C_FLAGS="-O2"
cmake --build lbzip2/build --target lbzip2 -j
```

(`-O2` is the canonical/fastest config — see Findings. `build/` is the adapter default.)

## Verify & benchmark (same as every other version)

```bash
python3 bench/verify.py bench/lbzip2_pbzx.sh data/<file>
python3 bench/run_bench.py --pbzx bench/lbzip2_pbzx.sh --inputs data/bench_large_1g.bin \
    --threads 1 2 4 8 16 32 64 96 144 --block-sizes 900000 --level 9 --repeat 3 \
    --out results/lbzip2_baseline_1gb.csv
```

Benchmark input: Silesia corpus tiled to 1.08 GB, ratio ≈ 0.261, representative
real-world text/binary mix. Regenerate (`data/` is gitignored):

```bash
curl -fsSL http://sun.aei.polsl.pl/~sdeor/corpus/silesia.zip -o /tmp/silesia.zip
unzip -oq /tmp/silesia.zip -d /tmp/silesia && cat /tmp/silesia/* > /tmp/cat.bin
: > data/bench_large_1g.bin
while [ "$(stat -c%s data/bench_large_1g.bin)" -lt 1082774528 ]; do cat /tmp/cat.bin >> data/bench_large_1g.bin; done
truncate -s 1082774528 data/bench_large_1g.bin
```

## Findings (profiling → optimization)

Machine: 2× Xeon 8352V, 72 physical / 144 logical cores.

1. **lbzip2 vs pbzx (head-to-head, identical 1.08 GB input, same ratio 0.261).**
   lbzip2 is faster at every thread count; `divsufsort` (suffix-array BWT) beats
   bzip2's blocksort:

   | threads |   1 |   2 |   4 |   8 |  16 |  32 |  64 |  96 | 144 |
   |---------|-----|-----|-----|-----|-----|-----|-----|-----|-----|
   | lbzip2 s|51.6 |26.4 |13.8 | 7.0 | 3.8 | 2.5 | 2.0 | 1.6 | 1.3 |
   | pbzx  s |85.6 |42.8 |21.6 |11.0 | 5.8 | 3.0 | 2.1 | 1.9 | 1.8 |
   | speedup |1.66 |1.62 |1.57 |1.57 |1.52 |1.21 |1.07 |1.19 |1.35 |

   (`results/lbzip2_baseline_1gb.csv`, `results/pbzx_compare_1gb.csv`.)
2. **Profile:** compute-bound — ~47% BWT (divsufsort), 10% encode, 5% Huffman EM;
   TopdownL1 = **84.7 % bad-speculation** (branch mispredicts in sort comparisons).
   Scales to ~888 MB/s @144t (42×), flattening past ~48t (SMT + memory-bandwidth bound).
3. **Optimization levers, measured rigorously (pinned-core medians):**
   `-O3 -march=native -funroll-loops` **regresses** (-O3 unrolling bloats hot loops);
   `-flto` neutral; **PGO** cut instructions but raised branch-misses → net slower;
   glibc malloc-tuning and `numactl --interleave` both slightly worse.
   → Stock **`-O2` is already optimal**; lbzip2 sits near the hardware ceiling.
4. Not lock-, allocator-, or NUMA-bound (each tested and excluded).

5. **`CLUSTER_FACTOR` (Huffman-EM iterations) — measured, not adopted.** Reducing
   8→4 (bzip2's default) gave ~5.3% faster single-thread compression for only
   0.086% larger output (ratio 0.25293→0.25315). We **keep the stock value (8)**
   so that, for a given input, lbzip2 produces byte-identical output regardless of
   build/thread count — reproducibility was preferred over a sub-ratio speed trade.

**Conclusion:** lbzip2 is a strong, well-optimized baseline that already beats our
pbzx, and the usual codegen / allocator / placement knobs do not move it on this
workload. We therefore ship the vendored lbzip2 **unmodified** (`lbzip2/src` matches
upstream); the contribution of this stage is the harness integration plus the
rigorous evidence that lbzip2 sits at the hardware ceiling here.
