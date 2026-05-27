#ifndef PBZX_ARGS_H
#define PBZX_ARGS_H
#include <stddef.h>

typedef struct {
    int    threads;     /* >= 1 */
    size_t block_size;  /* bytes, > 0 */
    int    level;       /* 1..9 -> libbz2 blockSize100k */
    const char *in_path;
    const char *out_path;
} Options;

/* Parse argv into opts (defaults applied first).
 * Returns 0 on success; nonzero on error (message printed to stderr). */
int args_parse(int argc, char **argv, Options *opts);
#endif
