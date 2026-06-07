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