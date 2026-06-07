#ifndef PBZX_PIPELINE_H
#define PBZX_PIPELINE_H
#include <stdio.h>
#include <stddef.h>

/* Block-level parallel compressor.
 *
 * Streams `in` as fixed-size blocks through a reader -> worker pool -> writer
 * pipeline. Each block is compressed into an independent .bz2 stream; the
 * writer concatenates them in original block-id order, so the output is
 * byte-identical to the sequential path regardless of `threads`.
 *
 *   threads   number of worker threads (>= 1)
 *   block_size  bytes per block (> 0)
 *   level       libbz2 blockSize100k (1..9)
 *   qdepth      max blocks in flight (bounds memory + reorder window; > 0)
 *
 * On success returns 0 and sets *out_input_bytes / *out_output_bytes.
 * Returns nonzero on I/O, allocation, or compression error. */
int pipeline_run(FILE *in, FILE *out, int threads, size_t block_size,
                 int level, size_t qdepth,
                 size_t *out_input_bytes, size_t *out_output_bytes);

#endif
