# pbzx Stage 3: Profiling-guided AI Parallelization

This is a sequential bzip2 compression tool called pbzx. Your goal is to
parallelize it and iteratively optimize it using profiling tools.

## Your task

Please parallelize this bzip2 compression program using multiple threads,
then use profiling tools to measure bottlenecks in your own implementation
and improve it. Repeat the profile → optimize → verify cycle until you are
satisfied with the performance.

## Permitted profiling tools

You have full permission to run any of these on `./pbzx` at any time:

- `perf stat -d ./pbzx ...` — hardware performance counters
- `perf record -g ./pbzx ... && perf report` — call-graph hotspots
- `valgrind --tool=callgrind ./pbzx ...` — instruction-level profiling
- `valgrind --tool=massif ./pbzx ...` — heap memory profiling
- `/usr/bin/time -v ./pbzx ...` — wall time + peak RSS + CPU%
- `strace -c ./pbzx ...` — system call summary
- `lscpu`, `nproc`, `free -h`, `getconf -a | grep -i cache` — machine info

## Source files you may modify

- `src/main.c` — main entry point and compression pipeline
- `src/writer.c` — writes compressed blocks to output
- `src/bz_block.c` / `src/bz_block.h` — per-block bzip2 compression
- `src/block_reader.c` / `src/block_reader.h` — reads input into fixed-size blocks
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

Expected: `PASS  <input_file>` — verify after every optimization round.

## Benchmark

```bash
python3 bench/run_bench.py --pbzx ./pbzx --inputs <input_file> \
  --threads 1 2 4 8 --block-sizes 900000 --level 9 --repeat 3 \
  --out results/stage3_results.csv
```

## Interface

```
./pbzx -i input.bin -o output.bz2 [--threads N] [--block-size B] [--level L]
```

`--threads 1` must still work correctly. Output must be valid bzip2.
