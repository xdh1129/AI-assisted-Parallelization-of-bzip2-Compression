# pbzx Stage 2: Constraint-guided AI Parallelization

This is a bzip2 compression tool called pbzx. Your goal is to parallelize it
using block-level parallelism, choosing design parameters informed by the actual
hardware this machine offers.

## Your task

Please parallelize the compressor using block-level parallelism.

Requirements:
1. Split the input file into fixed-size blocks.
2. Assign each block a unique block ID.
3. Use worker threads to compress blocks independently.
4. Use a writer thread (or equivalent ordered mechanism) to emit blocks in the original order.
5. Avoid race conditions and unnecessary global locks.
6. Avoid changing the compression result (decompressed output must match input exactly).
7. Before choosing thread count, block size, and queue depth, **run `lscpu`, `nproc`,
   `free -h`, and `getconf -a | grep -i cache`** to understand the machine hardware,
   then use those values as constraints in your implementation.

## Source files you may modify

- `src/main.c` — main entry point and compression pipeline
- `src/writer.c` — ordered output
- `src/bz_block.c` / `src/bz_block.h` — per-block compression (thread-safe: no global state)
- `src/block_reader.c` / `src/block_reader.h` — block reader
- `src/args.c` / `src/args.h` — argument parsing (already accepts `--threads N`)
- `Makefile` — update CFLAGS as needed
- You may add new `src/*.c` / `src/*.h` files

## Do NOT modify

- `third_party/bzip2/`
- `libbz2.a`

## Build

```bash
make clean && make all
```

Produces: `./pbzx`

## Test correctness

```bash
python3 bench/verify.py ./pbzx <input_file>
```

Expected: `PASS  <input_file>`

## Benchmark

```bash
python3 bench/run_bench.py --pbzx ./pbzx --inputs <input_file> \
  --threads 1 2 4 8 --block-sizes 900000 --level 9 --repeat 3 \
  --out results/stage2_results.csv
```

## Interface

```
./pbzx -i input.bin -o output.bz2 [--threads N] [--block-size B] [--level L]
```

`--threads 1` must still work correctly (single-threaded path).
Output must be valid bzip2.
