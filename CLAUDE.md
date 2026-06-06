# pbzx Stage 3: Profiling-guided AI Parallelization

This is a sequential bzip2 compression tool called pbzx. Your goal is to
parallelize it, using profiling data from a prior parallel implementation
as guidance for your design decisions.

## Your task

Please parallelize this bzip2 compression program using multiple threads.
Use the profiling data below to avoid known bottlenecks from the start.
You may also run profiling tools on your own implementation at any time.

## Profiling data from a prior parallel implementation

> [This section will be filled in with actual profiling findings before this
> agent session is opened. See `profiling/` directory for the raw data files.]

Raw profiling files are in `profiling/`:

| File | Contents |
|------|----------|
| `profiling/perf_stat.txt` | `perf stat -d` output — hardware counters |
| `profiling/time_v.txt` | `/usr/bin/time -v` — wall time, peak RSS, CPU% |
| `profiling/perf_report.txt` | `perf report --stdio` — call-graph hotspots |
| `profiling/scaling.txt` | Mean compress time at 1/2/4/8/N threads |

## Permitted profiling tools (run these on `./pbzx` at any time)

- `perf stat -d ./pbzx ...` — hardware performance counters
- `perf record -g ./pbzx ... && perf report` — call-graph flame data
- `valgrind --tool=callgrind ./pbzx ...` — instruction-level profiling
- `valgrind --tool=massif ./pbzx ...` — heap memory profiling
- `/usr/bin/time -v ./pbzx ...` — wall time + peak RSS
- `strace -c ./pbzx ...` — system call summary

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

Expected: `PASS  <input_file>`

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
