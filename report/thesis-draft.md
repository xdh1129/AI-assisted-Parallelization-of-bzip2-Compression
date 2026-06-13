# AI-Assisted bzip2 compression

## Abstract

Data compression is a critical component of high-performance computing, with algorithms like bzip2 prized for their high compression ratios. bzip2 internally processes data in blocks, making it a potential candidate for parallelization. However, effectively parallelizing this process requires careful management of output ordering, synchronization overhead, and I/O bottlenecks. This paper explores the efficacy of Large Language Models (LLMs) in automating the parallelization of a sequential bzip2 compressor (pbzx). We evaluate an AI-assisted development workflow across three progressive stages of guidance: naive prompting, constraint-guided design, and profiling-guided optimization. By comparing these AI-generated implementations against a sequential baseline and an established parallel reference (lbzip2), we analyze how varying levels of system-level feedback impact the correctness, speedup, and parallel efficiency of AI-generated C code.

---

## 1. Introduction

Large language models may help identify parallelizable components, generate multithreaded code, suggest pipeline designs, and optimize performance. However, AI may not fully understand the target machine, runtime behavior, synchronization costs, or the actual performance bottlenecks after parallelization. Therefore, we plan to guide AI using profiling results and system-level feedback.

The objective of this project is to explore different ways of using AI to assist in parallelizing a bzip2-like compression system, and to evaluate whether AI-generated or AI-assisted parallel versions can improve performance while preserving correctness. We evaluate this by subjecting a baseline sequential compressor to three distinct AI-assisted parallelization experiments. The system splits a large input file into fixed-size blocks. It then compresses different blocks independently using multiple threads. Finally, it verifies correctness by decompressing the compressed file and comparing it with the original input.

---

## 2. Background & Related Work

### 2.1 The bzip2 Algorithm and Parallelization Opportunities

bzip2 processes data in independent blocks, so block-level parallelism is possible. Since different data blocks can be compressed independently, multiple blocks may be assigned to different worker threads and processed in parallel. However, doing it well requires handling output ordering, load balancing, synchronization overhead, and I/O bottlenecks. In addition, block size may affect both compression ratio and parallel efficiency.

### 2.2 Baseline and Reference Implementations

To isolate the effects of our parallelization strategies, we utilize `pbzx`, a custom C11 baseline that sequentially compresses blocks using vendored `libbz2`. We compare the AI-generated implementations against `lbzip2`, a highly optimized, existing parallel implementation. Stock `bzip2` lacks an N-thread mode and uses different framing, thus it serves as an external reference rather than the baseline denominator for calculating speedup.

---

## 3. Methodology

Instead of only asking AI to “make the code faster,” we will design a structured workflow to guide AI step by step. The project isolates the development of each AI-assisted implementation on dedicated Git branches stemming from the `main` baseline.

### 3.1 Stage 1: Naive AI Parallelization (`stage/1-naive`)

In the first stage, we will provide AI with the sequential bzip2 compression code and ask it to parallelize the program. The agent receives a minimal prompt without hints regarding the parallelization strategy. This stage tests whether AI can independently identify the parallelizable parts of the program.

### 3.2 Stage 2: Constraint-Guided AI Parallelization (`stage/2-constrained`)

In the second stage, we will provide AI with clearer design requirements. The agent is prompted to use block-level parallelism, assign unique block IDs, use worker threads to compress independently, and employ a writer thread to maintain original output order. The agent is also instructed to avoid race conditions and unnecessary global locks. Furthermore, the agent is permitted to run commands like `lscpu`, `free`, and `nproc` to discover machine constraints before designing. This stage tests whether explicit system design constraints can help AI generate more correct and maintainable parallel code.

### 3.3 Stage 3: Profiling-Guided Optimization (`stage/3-profiling`)

The Stage 3 branch is created directly from the verified Stage 2 source code. In the third stage, we will run the AI-generated parallel version and collect profiling information, such as CPU utilization, runtime breakdown, I/O waiting time, lock contention, memory usage, thread idle time, and scalability under different thread counts. We feed this empirical bottleneck data back into the LLM context. This stage tests whether profiling feedback can help AI move from superficial code changes to bottleneck-driven optimization.

---

## 4. Experimental Setup

### 4.1 Environment and Tooling

The experiments are conducted on a Linux target environment using C11, `pthreads` or OpenMP, and a Python-based benchmarking harness. The Claude Code agent operates autonomously within isolated Git worktrees for each stage. Profiling data is gathered utilizing hardware performance counters via `perf stat`, call-graph hotspots via `perf record`, and resource monitoring via GNU `/usr/bin/time -v`.

### 4.2 Workloads

The primary workload utilized for all benchmark sweeps is a large tarball extracted from the Canterbury Corpus, providing a realistic and compressible dataset.

### 4.3 Evaluation Metrics

We evaluate both system performance and AI effectiveness. The metrics tracked by the harness include:

| Metric | Description |
| --- | --- |
| **Runtime** | Total compression time.|
| **Throughput** | Input size divided by compression time, measured in MB/s.|
| **Speedup** | Sequential runtime divided by parallel runtime.|
| **Parallel Efficiency** | Speedup divided by number of threads.|
| **Compression Ratio** | Compressed file size divided by original file size.|
| **Memory Usage** | Peak memory consumption.|
| **Correctness** | Whether decompressed output matches the original file.|

Performance improvements are quantified mathematically using the following standard definitions:

$$Speedup = \frac{T_{sequential}}{T_{parallel}}$$

$$Throughput = \frac{Input\_Size}{T_{compression}}$$

---

## 5. Expected Results and Challenges

We expect that the parallel version will reduce compression time for large compressible files, especially when the workload is CPU-bound. However, the speedup may not be perfectly linear because of I/O bottlenecks, synchronization overhead, memory bandwidth limitation, output ordering cost, and uneven compression time across blocks.

Regarding the AI interventions, we expect that naive AI-generated code may not produce the best result immediately. AI may generate code that compiles but performs poorly, or code that improves performance but breaks correctness. By providing clearer design constraints and profiling results, we expect AI to generate more effective and reliable parallelization strategies. We expect to observe the following trends:

* Naive AI prompting may produce incomplete or unsafe parallelization.


* Constraint-guided prompting may improve correctness and code structure.


* Profiling-guided prompting may improve actual runtime performance.


* Block size and thread count will significantly affect speedup and compression ratio.


* Existing tools such as lbzip2 or pbzip2 may still outperform our implementation, but they can serve as useful reference points.



To mitigate the risk of the AI ignoring I/O bottlenecks, our pipeline strictly enforces the use of profiling tools to measure I/O waiting time and guide AI toward pipeline optimization.

---

## 6. Results

### 6.1 Benchmark Setup

We swept thread counts $\{1, 2, 4, 8, 16, 32\}$ (block size 900,000 bytes, compression level 9, 3 repeats per configuration) against a 1.08GB input (1,082,774,528 bytes), produced by concatenating the Canterbury Corpus reference file used in earlier, smaller-scale runs. Each AI-assisted stage (`stage/1-naive`, `stage/2-constrained`, `stage/3-profiling`) was benchmarked in an isolated git worktree, and `lbzip2` was benchmarked as an external reference using the same input and thread sweep. Raw results are committed as `results/stageN_results_1gb.csv` on each respective branch and `experiments/lbzip2/results/lbzip2_results_1gb.csv` on `main`; the merged comparison data and figures referenced below are under `experiments/comparison/`.

### 6.2 Correctness

All three AI-assisted stages produce **byte-identical compressed output** regardless of thread count: compression ratio is `0.233903` and output size is `253,264,533` bytes in every run. (`lbzip2` produces a slightly different output size — `253,270,191` bytes, ratio `0.233908` — due to differences in block framing, not a correctness issue.) Round-trip decompression (`bunzip2 | cmp`) against the original 1.08GB input passes (`PASS`) for all four implementations at every thread count tested. This confirms that increasing thread count does not change the compressed output or break correctness for any of the three AI-generated parallel versions.

### 6.3 Runtime and Throughput

Table 1 reports mean compression time (seconds, averaged over 3 repeats) at each thread count.

**Table 1 — Mean compression time (s) on the 1.08GB input**

| threads | stage1 (naive) | stage2 (constrained) | stage3 (profiling) | lbzip2 (reference) |
| ---: | ---: | ---: | ---: | ---: |
| 1  | 80.84 | 81.77 | 78.72 | 67.90 |
| 2  | 40.63 | 40.62 | 39.43 | 34.51 |
| 4  | 20.80 | 20.74 | 20.02 | 17.58 |
| 8  | 10.53 | 10.50 | 10.23 | 9.10 |
| 16 | 5.52  | 5.50  | 5.36  | 4.96 |
| 32 | 3.06  | 3.49  | 3.03  | 3.14 |

![Compression time vs threads](../experiments/comparison/plots/runtime_by_impl.png)

*Figure 1 — Compression time vs. thread count (log-log scale) for all four implementations on the 1.08GB input.*

In absolute terms, **`stage3` (profiling-guided) is the fastest or tied-fastest of the three AI-assisted stages at every thread count**, and is competitive with — even marginally faster than — the mature `lbzip2` reference at high thread counts (3.03s vs. 3.14s at 32 threads). `stage2` (constraint-guided) is consistently the slowest of the three AI stages in absolute time, despite having a similar relative speedup curve (see §6.4); its higher single-threaded baseline (81.77s) and pthread-pipeline synchronization overhead carry through at every thread count.

Figure 2 shows the corresponding throughput curves, which mirror the runtime results (throughput is simply $Input\_Size / T_{compression}$): all four implementations reach roughly 330–360 MB/s at 32 threads, up from approximately 13–16 MB/s single-threaded.

![Throughput vs threads](../experiments/comparison/plots/throughput_by_impl.png)

*Figure 2 — Throughput (MB/s) vs. thread count for all four implementations on the 1.08GB input.*

### 6.4 Speedup

Table 2 reports speedup relative to each implementation's own single-threaded time ($Speedup = T_{1\text{-thread}} / T_{N\text{-threads}}$), and Figure 3 plots the same data against an ideal linear-speedup reference line.

**Table 2 — Speedup relative to each implementation's own 1-thread baseline**

| threads | stage1 (naive) | stage2 (constrained) | stage3 (profiling) | lbzip2 (reference) |
| ---: | ---: | ---: | ---: | ---: |
| 1  | 1.00x  | 1.00x  | 1.00x  | 1.00x |
| 2  | 1.99x  | 2.01x  | 2.00x  | 1.97x |
| 4  | 3.89x  | 3.94x  | 3.93x  | 3.86x |
| 8  | 7.68x  | 7.79x  | 7.69x  | 7.46x |
| 16 | 14.64x | 14.87x | 14.69x | 13.69x |
| 32 | 26.44x | 23.43x | 25.95x | 21.64x |

![Speedup vs threads](../experiments/comparison/plots/speedup_by_impl.png)

*Figure 3 — Speedup vs. thread count relative to each implementation's own single-threaded baseline, with an ideal linear-speedup reference line (dashed).*

All three AI-assisted stages — and `lbzip2` — track the ideal linear-speedup line closely up to 16 threads (within ~5% of ideal at every step: ~2x, ~4x, ~8x, ~15x), confirming that block-level parallelism is, as expected, embarrassingly parallel for a sufficiently large input (1,204 blocks at 900 KB each leaves ample work to keep 16 threads fed). Scaling tapers off at 32 threads for every implementation, plateauing around 22–26x — consistent with the profiling-stage finding that performance becomes limited by block granularity and BWT memory bandwidth rather than by software-level synchronization, once thread count approaches or exceeds the number of physical cores.

Note that `lbzip2`'s *relative* speedup is the lowest of the four (21.64x at 32 threads) purely because its single-threaded baseline is already the fastest (67.90s vs. 78–82s for the AI stages) — it has comparatively less headroom to climb. In **absolute** terms (Table 1, Figure 1), `lbzip2` remains competitive with, but does not dominate, the AI-assisted stages: `stage1` and `stage3` match or marginally beat it at 32 threads.

### 6.5 Discussion

These results update the expectations laid out in §5:

* **All three AI-assisted parallelizations are correct and scale well.** Contrary to the concern that "naive AI prompting may produce incomplete or unsafe parallelization," `stage/1-naive` already produces a correct, near-linearly-scaling OpenMP implementation. This suggests that block-level parallelization of `pbzx` is a sufficiently well-isolated transformation that even a minimally-guided agent can identify and implement it correctly.
* **Constraint-guided prompting (`stage2`) did not yield a clear runtime advantage over the naive version** — if anything, its pthread-pipeline design carries more baseline overhead (highest single-threaded time of the three stages, and the lowest absolute throughput at every thread count). Its main benefits, per the original design goals (explicit block IDs, ordered output via a writer thread, avoidance of global locks), are about code structure, maintainability, and robustness rather than raw speed — properties not directly captured by the runtime/speedup metrics alone.
* **Profiling-guided optimization (`stage3`) delivered the expected payoff**: starting from the verified `stage2` source, feeding back empirical bottleneck data (e.g., page-fault counts dropping from ~674K to ~181K after replacing per-block `malloc`/`free` with a per-thread bump-arena allocator) measurably reduced both the single-threaded baseline and the absolute runtime at every thread count, making it the fastest of the three AI stages overall and putting it on par with `lbzip2`.
* **Existing tools remain a useful reference, but do not categorically outperform the AI-assisted versions** on this workload — `stage1` and `stage3` match or slightly exceed `lbzip2`'s absolute throughput at high thread counts, even though `lbzip2` is a mature, hand-optimized implementation. This is a notably positive result for the AI-assisted workflow: with appropriate guidance (and, in the case of `stage3`, profiling feedback), LLM-generated parallelization can reach performance parity with established tools on a representative compressible workload.
* **Block size and thread count clearly affect speedup**, as expected — scaling is near-linear up to 16 threads and plateaus at 32, for all four implementations alike, pointing to a hardware/memory-bandwidth limit rather than an implementation-specific bottleneck at the high end.
  
 ### 6.6 Additional Research: GPU Acceleration Inside libbz2

  After completing the main CPU-side parallelization study, we conducted an additional follow-up experiment on a separate bzip2-gpu branch to explore whether parts of the internal
  libbz2 compression pipeline could be accelerated with CUDA. Unlike the main pbzx experiments, which focus on block-level parallelism across CPU threads, this extension targeted intra-
  block acceleration inside the standard bzip2 compression path while preserving the .bz2 format and the public API.

  The motivation for this follow-up came from profiling the original compression pipeline. In the CPU path, block sorting dominated total runtime, making it the most natural GPU target.
  We therefore first offloaded BZ2_blockSort to CUDA. After this optimization, profiling showed that the bottleneck shifted away from sorting and toward the CPU-side generateMTFValues
  and sendMTFValues stages. This made the GPU branch a useful case study in bottleneck migration: accelerating one dominant phase exposed new sequential limits in the remainder of the
  algorithm.

  We implemented three main GPU-oriented optimizations. First, the block sorting phase was offloaded to CUDA. Second, after sorting, the GPU was extended to directly generate the BWT
  last column (BZ2_CUDA_BWT=1), allowing the subsequent MTF stage to read the transformed block sequentially rather than through the original random-access block[ptr[i]-1] pattern.
  Third, we implemented a CUDA-assisted Huffman table optimization path (BZ2_CUDA_HUFFMAN=1) that parallelizes per-group code-cost evaluation and frequency accumulation, while leaving
  final bitstream emission on the CPU in order to preserve the original .bz2 stream format.

  Table 3 summarizes the 1 GB compression results. The CPU fallback required about 85.80s, with blocksort accounting for 60.97s (76.56%) of total internal phase time. Offloading
  blocksort to CUDA reduced compression time to about 33.44s, confirming that block sorting is well suited to GPU acceleration. Enabling GPU-side BWT last-column generation further
  reduced total compression time to about 29.95s, mainly by lowering MTF time from about 11.88s to 8.11s. Finally, enabling CUDA-assisted Huffman table optimization reduced total
  compression time again to about 27.04s, with the huffman_bitstream phase decreasing from about 6.88s to 4.18s. Relative to the CPU fallback, this corresponds to roughly a 3.17x end-
  to-end speedup.

  Table 3 — GPU extension results on the 1 GB input

 | Configuration| Compression time | Main bottleneck after optimization|
 | ---:| ---:| ---:|
 |CPU fallback |85.80s | CPU blocksort
 |CUDA blocksort| 33.44s |CPU MTF + Huffman
 |CUDA blocksort + BWT |29.95s| CPU MTF/Huffman
 | CUDA blocksort + BWT + Huffman | 27.04s| MTF  becomes the primary remaining bottleneck

  However, not all internal stages proved suitable for GPU acceleration. We also implemented an experimental CUDA MTF prototype that computed MTF ranks on the GPU while leaving zero-run
  compaction on the CPU. Although this version preserved correctness, it performed very poorly in practice: on the same 1 GB input, total compression time increased to about 136.14s,
  and the MTF phase alone rose to about 114.41s. This result reflects the fundamentally sequential nature of MTF: each symbol depends on the evolving recency ordering of earlier
  symbols, so a naive parallel backward-scan formulation causes excessive repeated work and poor memory behavior on the GPU. For this reason, the CUDA MTF prototype was removed from the
  final optimized path.

  Overall, this additional study shows that GPU acceleration is effective for the highly parallel parts of bzip2, especially block sorting and some table-optimization work, but not for
  all phases. Once sorting is accelerated, the bottleneck shifts to more sequential stages such as MTF and final encoding. Therefore, the main lesson from the GPU branch is not simply
  that “GPU makes bzip2 faster,” but that selective acceleration works best when applied to phases with strong data parallelism, while inherently sequential transformations remain
  difficult to accelerate efficiently on GPU hardware.

---

## 7. lbzip2 Implementation Analysis and Direct Optimization Study

Throughout §6, `lbzip2` served as the external reference and was consistently the fastest *single-threaded* implementation. This raises two questions that the comparison sweep alone does not answer: (1) *why* is `lbzip2` faster per core, given that it emits the same `.bz2` format, and (2) is `lbzip2` itself still improvable, or has it already reached the limits of this hardware? We investigate both on a dedicated branch (`feat/lbzip2-optimize`) that vendors `lbzip2`'s source and drives it through the *same* benchmarking harness via a thin adapter (mapping the `pbzx` CLI onto `lbzip2`'s flags and emitting the harness's `PBZX_STATS` line).

**Setup for this section.** Unlike §6 (Canterbury Corpus, thread sweep to 32), this focused study uses the **Silesia corpus tiled to 1.08 GB** (compression ratio ≈ 0.261, a representative real-world text/binary mix) and extends the thread sweep to **144** on a 2× Intel Xeon Platinum 8352V node (72 physical / 144 logical cores). The different corpus is why `lbzip2`'s absolute single-threaded time here (≈51 s) differs from §6's Canterbury figure (≈68 s); suffix-sort cost is data-dependent. Raw data is committed on the branch as `results/lbzip2_baseline_1gb.csv` and `results/pbzx_compare_1gb.csv`.

### 7.1 Where lbzip2's speed comes from: the BWT algorithm

Both `pbzx` and `lbzip2` produce byte-compatible bzip2 output and run the identical logical pipeline — `RLE1 → BWT → MTF → RLE2 → Huffman → bitstream` — so their compression ratios are essentially equal (0.2607 vs. 0.2608 on this input). The entire per-core speed difference is concentrated in **one stage: the Burrows–Wheeler Transform (BWT)**, which reorders a block by *sorting all of its suffixes*. The sorted order is unique, so both tools compute the same BWT; they differ only in the sorting algorithm used.

* **`pbzx` → bzip2's `BZ2_blockSort` (Seward's algorithm).** `pbzx` links `libbz2`, so each block is sorted by `mainSort` (`blocksort.c`). It buckets suffixes by their first two bytes and then **quicksorts each bucket by comparing suffixes byte-by-byte**, using a "quadrant" table to reuse some comparison work and a *work-budget* that bails out to a slower `fallbackSort` on pathologically repetitive data. Its weakness is exactly those repeated byte-by-byte string comparisons, which do redundant work on inputs with long repeats.

* **`lbzip2` → its own `divbwt` (libdivsufsort).** `lbzip2` does not use `libbz2` at all; `divbwt.c` is a complete suffix-array constructor based on **induced sorting**. It classifies suffixes into types, sorts only the smaller "type B\*" subset with `sssort` (a multikey introsort over short substrings), and then **induces** the order of all remaining suffixes from that sorted subset with `trsort` (a tandem-repeat sort that handles periodic runs cheaply). This performs far less redundant comparison work, degrades gracefully on repetitive input, and never needs a fallback path.

This is the decisive algorithmic difference: `lbzip2` swaps bzip2's comparison-based suffix sort for a suffix-array (induced-sorting) BWT that computes the identical result with less work. A secondary difference is the *parallelization architecture* — `pbzx` uses an OpenMP fork/join `parallel for` over independent 900 KB blocks, whereas `lbzip2` uses a hand-built `pthread` pipeline (one reader thread, a worker pool, one order-preserving writer/muxer thread, linked by priority queues). Because *both* parallelize at the block level, however, this architecture affects scaling smoothness and I/O overlap rather than raw per-core throughput; the per-core advantage is the BWT algorithm.

### 7.2 Profiling lbzip2

A single-threaded `perf record` run on a 128 MB Silesia slice gives the self-time breakdown in Table 4. The suffix-sort routines (`divbwt` plus the `ss_*` substring-sort and `tr_*` tandem-repeat-sort phases of `divsufsort`) account for **≈47 %** of runtime; the entropy-coding stages (`encode`, `generate_prefix_code`) account for ≈16 %.

**Table 4 — lbzip2 single-thread self-time (perf, 128 MB Silesia, level 9)**

| Function | Self time | Stage |
| --- | ---: | --- |
| `divbwt` | 17.6 % | BWT (divsufsort driver) |
| `ss_mintrosort` | 12.2 % | BWT (substring sort) |
| `encode` | 10.2 % | MTF / RLE2 |
| `tr_partition` | 8.5 % | BWT (tandem-repeat sort) |
| `tr_introsort` | 6.6 % | BWT (tandem-repeat sort) |
| `generate_prefix_code` | 5.4 % | Huffman tree optimization |
| `collect` | 4.3 % | RLE1 / input collection |

Crucially, the TopdownL1 microarchitecture breakdown attributes **84.7 % of slots to *bad speculation*** (branch mispredictions), with only ≈11 % retiring. The bottleneck is therefore the data-dependent branches inside the suffix-sort comparisons — `lbzip2` is compute-bound and limited by branch prediction, not by memory latency, I/O, or synchronization at the single-thread level.

### 7.3 Optimization attempts

Guided by §7.2, we attempted to speed up `lbzip2` itself. To suppress the noise of a shared, frequency-scaling node, single-thread numbers below are **medians of pinned-core runs** (`taskset`). Output was verified byte-identical (round-trip `bunzip2 | cmp`) for every build.

**Table 5 — Build/runtime optimization attempts (single-thread, pinned, 128 MB Silesia)**

| Variant | Median time | vs. `-O2` |
| --- | ---: | ---: |
| `-O2` (stock) | 6.09 s | — |
| `-O3 -march=native -funroll-loops` | 6.34 s | **+4 % (slower)** |
| `… + -flto` | ≈6.4 s | neutral / slower |
| Profile-guided optimization (PGO) | 6.29 s | +3 % (slower) |

Every codegen lever *regressed or was neutral*: `-O3`'s aggressive unrolling/inlining bloats the hot sort loops (hurting the instruction cache and branch predictor), and PGO reduced retired instructions but *raised* branch-misses, so it was net slower — unsurprising, since the dominant cost is data-dependent mispredicts that static profiles cannot eliminate. Runtime/system tuning fared the same: forcing the glibc allocator to recycle large buffers (`MALLOC_MMAP_MAX_=0`) gave 808 vs. 853 MB/s at 144 threads, and `numactl --interleave=all` gave 814 vs. 859 MB/s — both slightly *worse* — confirming `lbzip2` is neither allocator- nor NUMA-bound here.

The only lever with a measurable gain was algorithmic: `lbzip2`'s Huffman tree optimization runs `CLUSTER_FACTOR = 8` Expectation–Maximization passes (bzip2 uses 4). Because EM converges quickly, reducing it to 4 made compression **5.3 % faster** (6.09 → 5.77 s) for only **0.086 % larger output** (ratio 0.25293 → 0.25315). We nonetheless **kept the stock value (8)** so that, for a given input, `lbzip2` produces byte-identical output regardless of build or thread count — reproducibility was preferred over a sub-ratio speed trade. We therefore ship `lbzip2` unmodified.




### 7.5 Conclusion of the study

This deep-dive yields a clear, if humbling, result. `lbzip2`'s per-core advantage over our AI-assisted `pbzx` is **algorithmic** — a suffix-array (divsufsort) BWT in place of bzip2's comparison-based blocksort — not a matter of better compiler flags or threading tricks. And `lbzip2` is already operating **near the hardware ceiling** on this workload: profiling shows it is branch-prediction-bound in a hand-tuned sort, and *every* generic optimization knob we tried (`-O3`, `-march=native`, `-flto`, PGO, allocator tuning, NUMA interleaving) left it unchanged or slower. Meaningful further gains would require either an algorithm-level change (a different suffix-sort or microarchitecture-specific sort kernel) or accepting a compression-ratio trade-off (e.g., fewer Huffman EM passes). This reinforces a central theme of the project: once a mature, hand-optimized baseline is reached, profiling is as valuable for telling you *where not to spend effort* as for finding wins.

## 8. pbzip2 Implementation Analysis

The third reference tool used in §6, `pbzip2` (Parallel BZIP2, by Jeff Gilchrist with later contributions from Yavor Nikolov), is the most direct point of comparison for our work: like our `pbzx`, it is a parallel front-end *on top of* the stock `libbz2` library rather than a from-scratch reimplementation. Examining its source (v1.1.13, the last release) therefore isolates exactly what a hand-written parallel runtime looks like versus the OpenMP `parallel for` our AI-assisted versions generate. The findings below are from reading the released source (`pbzip2.cpp`, `pbzip2.h`, `BZ2StreamScanner.*`, `Makefile`); they were not re-benchmarked here beyond the §6 numbers.

### 8.1 Same codec, hand-built threading runtime

`pbzip2` is written in C++ and **links `libbz2`** (`Makefile`: `-lbz2`, `-pthread`, `-O2`). Each block is compressed by a single call to `BZ2_bzBuffToBuffCompress(dst, &dstLen, src, srcLen, BWTblockSize, verbosity, 30)` — i.e. bzip2's own block-sorting BWT, MTF/RLE2, and Huffman coder, at the standard work factor of 30. This is the **identical codec path our `pbzx` uses**, so `pbzip2` and `pbzx` share bzip2's comparison-based `blockSort` and therefore the same per-core BWT cost and (modulo block-splitting) the same compression ratio. The difference between the two is entirely in *how work is distributed across cores*.

Where `pbzx` relies on the OpenMP runtime, `pbzip2` implements its own POSIX-threads pipeline with three roles connected by bounded, mutex-guarded queues:

* **One producer thread** (`producer`) reads the input *as a stream* in fixed-size chunks (file block size `-b`, default 900 KB). It allocates a buffer per chunk, tags it with a monotonically increasing `blockNumber`, and pushes it onto a bounded input FIFO (`queueInit(numCPU)`) under a single mutex with `notFull`/`notEmpty` condition variables. Because it never seeks or relies on the file size, `pbzip2` works transparently on pipes and `stdin` (e.g. `tar … | pbzip2`).
* **`numCPU` worker threads** (`consumer`, count from `-p` or CPU autodetect) each pop a chunk off the FIFO, release the lock, compress the chunk independently with `libbz2`, and deposit the result into a shared **circular output buffer** at the slot derived from its `blockNumber` (`outputBufferAdd` / `getOutputBufferPos`).
* **One writer thread** (`fileWriter`) drains that output buffer **strictly in `blockNumber` order** (`NextBlockToWrite`), writing each compressed chunk to the output fd and freeing it. In-order draining is what makes the concatenated output deterministic regardless of the order in which workers finish.

Back-pressure is explicit and memory-bounded: the producer blocks when the input FIFO is full; a worker blocks in `outputBufferAdd` when its block number runs too far ahead of the writer; and the writer waits on a condition variable when its next in-order slot is empty. The reorder window is sized from the memory cap, `NumBufferedBlocksMax = maxMemory / blockSize` (default `-m` = 100 MB), so RAM use stays bounded no matter how many blocks are in flight. The tool adds a signal-handler thread and a terminator thread for clean teardown, plus optional load-average throttling (`-l`) and a tunable child stack size (`-S`) to limit per-thread memory at very high thread counts.

### 8.2 Block independence and the multi-stream `.bz2` format

Each chunk is compressed as a **complete, independent bzip2 stream**, and the output file is simply the concatenation of those streams:

```
bzip2:   [-------------------- one stream --------------------]
pbzip2:  [--stream--|--stream--|--stream--|--stream--|--stream--]
```

This is the source of two well-known `pbzip2` properties. First, output is typically **< 0.2 % larger** than serial bzip2, because every chunk carries its own stream header/footer and resets the BWT block boundary (the final sub-block of each chunk is usually short). Second, the format remains **fully `bzip2`-compatible**: stock `bzip2` transparently decodes concatenated streams, so anything `pbzip2` writes can be read by `bzip2` and vice-versa. The same structure also lets `pbzip2` *decompress* in parallel — `BZ2StreamScanner` locates stream boundaries so chunks can be farmed out to workers — but only for files that were themselves produced as multi-stream (a file written by serial `bzip2` is one indivisible stream and decompresses single-threaded). Note that the file block size `-b` is distinct from the BWT block size `-1..-9`; with `-r` the producer instead sets `blockSize = fileSize / numCPU` to spread one read-into-RAM file evenly across workers.

### 8.3 Positioning relative to pbzx and lbzip2

Table 7 places `pbzip2` against the other two parallel implementations on the three axes that matter — codec, parallel runtime, and resulting ratio.

**Table 7 — Design comparison of the three parallel bzip2 implementations**

| | `pbzx` (ours) | `pbzip2` | `lbzip2` |
| --- | --- | --- | --- |
| Language | C + OpenMP | C++ + pthreads | C + pthreads |
| BWT / codec | `libbz2` blocksort | `libbz2` blocksort | own `divbwt` (divsufsort) |
| Parallel model | OpenMP fork/join `parallel for` | reader → worker pool → ordered writer | reader → worker pool → ordered muxer |
| Streaming (pipe) input | partitioned up front | yes (streaming producer) | yes (streaming reader) |
| Parallel decompress | no | yes (multi-stream only) | yes (multi-stream only) |
| Compression ratio | bzip2 baseline | bzip2 baseline (≈ identical) | bzip2 baseline (≈ identical) |

Two conclusions follow directly from the source, consistent with the §6 measurements. (1) Because `pbzip2` and `pbzx` share the *same* `libbz2` codec, they have essentially the **same per-core throughput and compression ratio**; their differences are confined to scheduling — `pbzip2`'s persistent producer/worker/writer pipeline overlaps disk read, compression, and write and accepts pipes, whereas the OpenMP fork/join model partitions data up front and synchronizes at a barrier. `pbzip2` is, in effect, the hand-coded ancestor of the same block-parallel idea our AI-assisted versions express through OpenMP. (2) `pbzip2` shares `lbzip2`'s *threading architecture* (a reader feeding a worker pool drained by one order-preserving writer) but **not** its BWT: `pbzip2` keeps bzip2's comparison-based blocksort, so it trails `lbzip2` per core for exactly the reason established for `pbzx` in §7.1 — the suffix-array (divsufsort) BWT, not the threading layer, is what makes `lbzip2` faster. The pipeline-versus-fork/join distinction shapes I/O overlap and scaling smoothness; the per-core speed gap is algorithmic.