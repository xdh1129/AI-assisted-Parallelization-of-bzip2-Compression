#ifndef PBZX_WRITER_H
#define PBZX_WRITER_H
#include <stdio.h>
#include <stdint.h>
#include <stddef.h>

/* A compressed block indexed by its block id. */
typedef struct {
    uint8_t *data;  /* compressed bytes; owned by caller */
    size_t   len;
} CompressedBlock;

/* Write blocks[0..count-1] to f in ascending index order (concatenation).
 * Zero-length entries are skipped. Returns 0 on success, nonzero on I/O error. */
int write_blocks_in_order(FILE *f, const CompressedBlock *blocks, size_t count);
#endif
