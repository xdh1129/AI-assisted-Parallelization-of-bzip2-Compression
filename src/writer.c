#include "writer.h"

int write_blocks_in_order(FILE *f, const CompressedBlock *blocks, size_t count) {
    for (size_t i = 0; i < count; i++) {
        if (blocks[i].len == 0) continue;
        if (fwrite(blocks[i].data, 1, blocks[i].len, f) != blocks[i].len)
            return 1;
    }
    return 0;
}
