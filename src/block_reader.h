#ifndef PBZX_BLOCK_READER_H
#define PBZX_BLOCK_READER_H
#include <stdio.h>
#include <stdint.h>
#include <stddef.h>

typedef struct {
    uint8_t *data;  /* malloc'd; owned by caller */
    size_t   len;   /* bytes in this block (<= block_size) */
    uint32_t id;    /* 0-based index */
} Block;

/* Read the whole file into blocks of at most block_size bytes.
 * On success returns 0 and sets *out_blocks (malloc'd array, may be NULL if
 * empty) and *out_count. Empty file => count 0. Nonzero on I/O/alloc error. */
int read_all_blocks(FILE *f, size_t block_size,
                    Block **out_blocks, size_t *out_count);

void free_blocks(Block *blocks, size_t count);
#endif
