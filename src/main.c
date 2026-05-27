#include <stdio.h>
#include <stdlib.h>
#include <time.h>
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

    size_t input_bytes = 0;
    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);

    int err = 0;
    /* Sequential path. The parallel stage replaces this loop with
     * `#pragma omp parallel for` (each iteration writes its own slot). */
    for (size_t i = 0; i < n; i++) {
        const uint8_t *src = empty_input ? NULL : blocks[i].data;
        size_t len = empty_input ? 0 : blocks[i].len;
        input_bytes += len;
        if (compress_block(src, len, opt.level, &comp[i].data, &comp[i].len) != 0) {
            err = 1; break;
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
