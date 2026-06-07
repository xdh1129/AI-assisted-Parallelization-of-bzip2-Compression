#define _POSIX_C_SOURCE 199309L
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#ifdef _OPENMP
#include <omp.h>
#endif
#include "args.h"
#include "block_reader.h"
#include "bz_block.h"
#include "writer.h"

static void free_comp(CompressedBlock *c, size_t n) {
    if (!c) return;
    for (size_t i = 0; i < n; i++) free(c[i].data);
    free(c);
}

int main(int argc, char **argv) {
    Options opt;
    if (args_parse(argc, argv, &opt) != 0) return 2;

    FILE *in = fopen(opt.in_path, "rb");
    if (!in) { perror("pbzx: open input"); return 3; }

    Block *blocks = NULL; size_t nblocks = 0;
    if (read_all_blocks(in, opt.block_size, &blocks, &nblocks) != 0) {
        fprintf(stderr, "pbzx: read error\n"); fclose(in); return 4;
    }
    fclose(in);

    /* Empty input still emits one valid empty .bz2 stream so output round-trips. */
    int empty_input = (nblocks == 0);
    size_t n = empty_input ? 1 : nblocks;

    CompressedBlock *comp = (CompressedBlock *)calloc(n, sizeof(CompressedBlock));
    if (!comp) { fprintf(stderr, "pbzx: oom\n"); free_blocks(blocks, nblocks); return 5; }

    /* Computed up front (not inside the compress loop) so the loop carries no
     * shared mutable state and can become `#pragma omp parallel for`. */
    size_t input_bytes = 0;
    if (!empty_input)
        for (size_t i = 0; i < nblocks; i++) input_bytes += blocks[i].len;

    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);

    int err = 0;
    /* Parallel path. Each iteration writes only its own comp[i] slot (no shared
     * writes), so blocks compress independently across threads. Two adaptations
     * make the loop OpenMP-safe:
     *   - the original `break` on error is illegal in an omp for; instead each
     *     iteration is guarded by `if (!err)` and sets err via `#pragma omp
     *     atomic write`. We can't stop early, but later iterations skip the work;
     *   - input_bytes is summed above, not here, to avoid a loop-carried
     *     reduction. */
#ifdef _OPENMP
    omp_set_num_threads(opt.threads);
#endif
    #pragma omp parallel for schedule(dynamic)
    for (size_t i = 0; i < n; i++) {
        if (err) continue;
        const uint8_t *src = empty_input ? NULL : blocks[i].data;
        size_t len = empty_input ? 0 : blocks[i].len;
        if (compress_block(src, len, opt.level, &comp[i].data, &comp[i].len) != 0) {
            #pragma omp atomic write
            err = 1;
        }
    }
    clock_gettime(CLOCK_MONOTONIC, &t1);

    if (err) {
        fprintf(stderr, "pbzx: compression failed\n");
        free_comp(comp, n); free_blocks(blocks, nblocks); return 6;
    }

    FILE *out = fopen(opt.out_path, "wb");
    if (!out) {
        perror("pbzx: open output");
        free_comp(comp, n); free_blocks(blocks, nblocks); return 7;
    }
    if (write_blocks_in_order(out, comp, n) != 0) {
        fprintf(stderr, "pbzx: write error\n"); fclose(out);
        free_comp(comp, n); free_blocks(blocks, nblocks); return 8;
    }
    long output_bytes = ftell(out);
    fclose(out);

    double secs = (t1.tv_sec - t0.tv_sec) + (t1.tv_nsec - t0.tv_nsec) / 1e9;
    printf("PBZX_STATS input_bytes=%zu output_bytes=%ld block_size=%zu "
           "threads=%d level=%d blocks=%zu compress_seconds=%.6f\n",
           input_bytes, output_bytes, opt.block_size, opt.threads,
           opt.level, n, secs);

    free_comp(comp, n); free_blocks(blocks, nblocks);
    return 0;
}
