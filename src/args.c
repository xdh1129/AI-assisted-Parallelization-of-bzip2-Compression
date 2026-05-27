#include "args.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int args_parse(int argc, char **argv, Options *opts) {
    opts->threads = 1;
    opts->block_size = 900000;
    opts->level = 9;
    opts->in_path = NULL;
    opts->out_path = NULL;

    for (int i = 1; i < argc; i++) {
        const char *a = argv[i];
        if (strcmp(a, "-i") == 0 && i + 1 < argc) {
            opts->in_path = argv[++i];
        } else if (strcmp(a, "-o") == 0 && i + 1 < argc) {
            opts->out_path = argv[++i];
        } else if (strcmp(a, "--threads") == 0 && i + 1 < argc) {
            opts->threads = atoi(argv[++i]);
        } else if (strcmp(a, "--block-size") == 0 && i + 1 < argc) {
            opts->block_size = (size_t)strtoull(argv[++i], NULL, 10);
        } else if (strcmp(a, "--level") == 0 && i + 1 < argc) {
            opts->level = atoi(argv[++i]);
        } else {
            fprintf(stderr, "pbzx: unknown or incomplete option: %s\n", a);
            return 1;
        }
    }
    if (!opts->in_path)  { fprintf(stderr, "pbzx: -i input required\n"); return 1; }
    if (!opts->out_path) { fprintf(stderr, "pbzx: -o output required\n"); return 1; }
    if (opts->threads < 1) { fprintf(stderr, "pbzx: --threads must be >= 1\n"); return 1; }
    if (opts->block_size == 0) { fprintf(stderr, "pbzx: --block-size must be > 0\n"); return 1; }
    if (opts->level < 1 || opts->level > 9) { fprintf(stderr, "pbzx: --level must be 1..9\n"); return 1; }
    return 0;
}
