#ifndef PBZX_BZ_BLOCK_H
#define PBZX_BZ_BLOCK_H
#include <stdint.h>
#include <stddef.h>

/* Compress one block into a standalone .bz2 stream.
 * level is 1..9 (libbz2 blockSize100k). Allocates *out (caller frees).
 * in may be NULL iff in_len == 0. Returns 0 on success, nonzero on error. */
int compress_block(const uint8_t *in, size_t in_len, int level,
                   uint8_t **out, size_t *out_len);
#endif
