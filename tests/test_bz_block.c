#include <assert.h>
#include <string.h>
#include <stdlib.h>
#include <stdint.h>
#include <bzlib.h>
#include "../src/bz_block.h"

static void roundtrip(const char *data, size_t len) {
    uint8_t *comp; size_t comp_len;
    assert(compress_block((const uint8_t *)data, len, 9, &comp, &comp_len) == 0);
    assert(comp_len > 0);

    unsigned int cap = (unsigned int)(len == 0 ? 1 : len);
    char *out = (char *)malloc(cap);
    assert(out);
    unsigned int got = cap;
    int rc = BZ2_bzBuffToBuffDecompress(out, &got,
                                        (char *)comp, (unsigned int)comp_len, 0, 0);
    assert(rc == BZ_OK);
    assert(got == len);
    if (len) assert(memcmp(out, data, len) == 0);
    free(out); free(comp);
}

int main(void) {
    roundtrip("hello world hello world hello world", 35);
    roundtrip("", 0);

    static char big[900000];
    memset(big, 'A', sizeof(big));
    roundtrip(big, sizeof(big));
    return 0;
}
