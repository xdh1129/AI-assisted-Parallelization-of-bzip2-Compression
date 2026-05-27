#include "block_reader.h"
#include <stdlib.h>

void free_blocks(Block *blocks, size_t count) {
    if (!blocks) return;
    for (size_t i = 0; i < count; i++) free(blocks[i].data);
    free(blocks);
}

int read_all_blocks(FILE *f, size_t block_size,
                    Block **out_blocks, size_t *out_count) {
    Block *blocks = NULL;
    size_t count = 0, cap = 0;

    for (;;) {
        uint8_t *buf = (uint8_t *)malloc(block_size);
        if (!buf) { free_blocks(blocks, count); return 1; }

        size_t n = fread(buf, 1, block_size, f);
        if (n == 0) {
            free(buf);
            if (ferror(f)) { free_blocks(blocks, count); return 1; }
            break; /* clean EOF */
        }
        if (count == cap) {
            size_t ncap = cap ? cap * 2 : 8;
            Block *nb = (Block *)realloc(blocks, ncap * sizeof(Block));
            if (!nb) { free(buf); free_blocks(blocks, count); return 1; }
            blocks = nb; cap = ncap;
        }
        blocks[count].data = buf;
        blocks[count].len = n;
        blocks[count].id = (uint32_t)count;
        count++;
    }

    *out_blocks = blocks;
    *out_count = count;
    return 0;
}
