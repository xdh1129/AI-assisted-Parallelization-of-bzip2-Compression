#include "bz_block.h"
#include <stdlib.h>
#include <bzlib.h>

int compress_block(const uint8_t *in, size_t in_len, int level,
                   uint8_t **out, size_t *out_len) {
    /* bzip2 worst-case output: in_len + in_len/100 + 600 */
    unsigned int dest_len = (unsigned int)(in_len + in_len / 100 + 600);
    uint8_t *buf = (uint8_t *)malloc(dest_len);
    if (!buf) return 1;

    static uint8_t empty[1] = {0};
    char *src = (char *)(in_len ? (const char *)in : (const char *)empty);

    int rc = BZ2_bzBuffToBuffCompress((char *)buf, &dest_len,
                                      src, (unsigned int)in_len,
                                      level, 0, 0);
    if (rc != BZ_OK) { free(buf); return 1; }

    *out = buf;
    *out_len = dest_len;
    return 0;
}
