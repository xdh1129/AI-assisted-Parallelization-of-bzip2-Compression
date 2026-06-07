#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>
#include "args.h"
#include "block_reader.h"
#include "bz_block.h"
#include "writer.h"
#include "pipeline.h"

/* Hardware constraints measured on this machine (lscpu / nproc / free -h /
 * getconf), used to bound the runtime parameters below:
 *   - CPUs:   144 logical = 72 physical cores (2 sockets x 36) x 2 SMT threads.
 *             -> worker count is clamped to the online CPU count; past that,
 *                extra threads only add scheduling/cache contention.
 *   - Memory: ~755 GiB total, ~626 GiB free. Memory is NOT the binding
 *             constraint, so the in-flight queue depth is sized for throughput
 *             (keep every worker fed plus reader/writer overlap) rather than to
 *             cap RAM: qdepth = threads x QDEPTH_PER_THREAD.
 *   - Cache:  L1d 48 KiB/core, L2 1.25 MiB/core, L3 54 MiB/socket. The default
 *             900 KB block matches bzip2's largest window (level 9 = 900k);
 *             one block's working set is per-worker and stays within a core's
 *             private L2 + shared L3 budget even at full thread count. */
#define QDEPTH_PER_THREAD 4

static void free_comp(CompressedBlock *c, size_t n) {
    if (!c) return;
    for (size_t i = 0; i < n; i++) free(c[i].data);
    free(c);
}

/* Genuine single-threaded path: no threads created. Kept separate so that
 * `--threads 1` exercises a simple, easy-to-audit sequential pipeline. */
static int run_sequential(const Options *opt, FILE *in, FILE *out,
                          size_t *input_bytes, size_t *output_bytes) {
    Block *blocks = NULL; size_t nblocks = 0;
    if (read_all_blocks(in, opt->block_size, &blocks, &nblocks) != 0) {
        fprintf(stderr, "pbzx: read error\n");
        return 1;
    }

    /* Empty input still emits one valid empty .bz2 stream so output round-trips. */
    int empty_input = (nblocks == 0);
    size_t n = empty_input ? 1 : nblocks;

    CompressedBlock *comp = (CompressedBlock *)calloc(n, sizeof(CompressedBlock));
    if (!comp) { fprintf(stderr, "pbzx: oom\n"); free_blocks(blocks, nblocks); return 1; }

    size_t in_bytes = 0;
    for (size_t i = 0; i < nblocks; i++) in_bytes += blocks[i].len;

    int err = 0;
    for (size_t i = 0; i < n; i++) {
        const uint8_t *src = empty_input ? NULL : blocks[i].data;
        size_t len = empty_input ? 0 : blocks[i].len;
        if (compress_block(src, len, opt->level, &comp[i].data, &comp[i].len) != 0) {
            err = 1; break;
        }
    }
    if (err) {
        fprintf(stderr, "pbzx: compression failed\n");
        free_comp(comp, n); free_blocks(blocks, nblocks); return 1;
    }

    if (write_blocks_in_order(out, comp, n) != 0) {
        fprintf(stderr, "pbzx: write error\n");
        free_comp(comp, n); free_blocks(blocks, nblocks); return 1;
    }
    size_t out_bytes = 0;
    for (size_t i = 0; i < n; i++) out_bytes += comp[i].len;

    *input_bytes = in_bytes;
    *output_bytes = out_bytes;
    free_comp(comp, n); free_blocks(blocks, nblocks);
    return 0;
}

int main(int argc, char **argv) {
    Options opt;
    if (args_parse(argc, argv, &opt) != 0) return 2;

    /* Clamp the worker count to the online CPUs (hardware constraint). */
    long ncpu = sysconf(_SC_NPROCESSORS_ONLN);
    if (ncpu > 0 && opt.threads > (int)ncpu) {
        fprintf(stderr, "pbzx: clamping --threads %d to %ld online CPUs\n",
                opt.threads, ncpu);
        opt.threads = (int)ncpu;
    }

    FILE *in = fopen(opt.in_path, "rb");
    if (!in) { perror("pbzx: open input"); return 3; }
    FILE *out = fopen(opt.out_path, "wb");
    if (!out) { perror("pbzx: open output"); fclose(in); return 7; }

    size_t input_bytes = 0, output_bytes = 0;
    size_t qdepth = (size_t)opt.threads * QDEPTH_PER_THREAD;

    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);

    int rc;
    if (opt.threads <= 1) {
        rc = run_sequential(&opt, in, out, &input_bytes, &output_bytes);
    } else {
        rc = pipeline_run(in, out, opt.threads, opt.block_size, opt.level,
                          qdepth, &input_bytes, &output_bytes);
        if (rc != 0) fprintf(stderr, "pbzx: parallel compression failed\n");
    }
    clock_gettime(CLOCK_MONOTONIC, &t1);

    fclose(in);
    if (fclose(out) != 0 && rc == 0) { perror("pbzx: close output"); rc = 8; }
    if (rc != 0) return 6;

    /* Fixed-size blocks => exact ceil; empty input is one (empty) block. */
    size_t blocks = input_bytes ? (input_bytes + opt.block_size - 1) / opt.block_size : 1;

    double secs = (t1.tv_sec - t0.tv_sec) + (t1.tv_nsec - t0.tv_nsec) / 1e9;
    printf("PBZX_STATS input_bytes=%zu output_bytes=%zu block_size=%zu "
           "threads=%d level=%d blocks=%zu compress_seconds=%.6f\n",
           input_bytes, output_bytes, opt.block_size, opt.threads,
           opt.level, blocks, secs);
    return 0;
}
