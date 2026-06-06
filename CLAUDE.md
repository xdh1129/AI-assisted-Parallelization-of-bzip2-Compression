# pbzx Stage 1: Naive AI Parallelization

This is a bzip2 compression tool called pbzx.

## Your task

Please parallelize this bzip2 compression program using multiple threads.
Preserve correctness and improve performance.

## Source files you may modify

- `src/main.c` — main entry point and compression pipeline
- `src/writer.c` — writes compressed blocks to output
- `src/bz_block.c` / `src/bz_block.h` — per-block bzip2 compression
- `src/block_reader.c` / `src/block_reader.h` — reads input into fixed-size blocks
- `src/args.c` / `src/args.h` — argument parsing (already accepts `--threads N`)
- `Makefile` — update CFLAGS here if you need new compiler flags (e.g. `-fopenmp`, `-lpthread`)

## Do NOT modify

- `third_party/bzip2/` — vendored libbz2 source
- `libbz2.a` — prebuilt static library

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
  --out results/stage1_results.csv
```

## Interface

```
./pbzx -i input.bin -o output.bz2 [--threads N] [--block-size B] [--level L]
```

The `--threads` flag is parsed but currently unused in the compression step.
Output must be valid bzip2: `bunzip2 -c output.bz2 | cmp - input.bin` must succeed.
`--threads 1` must behave identically to the original sequential code.
