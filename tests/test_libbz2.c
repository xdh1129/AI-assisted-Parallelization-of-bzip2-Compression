#include <assert.h>
#include <string.h>
#include <bzlib.h>

int main(void) {
    const char *msg = "hello bzip2 hello bzip2 hello bzip2 hello bzip2";
    unsigned int in_len = (unsigned int)strlen(msg);

    char comp[512];
    unsigned int comp_len = sizeof(comp);
    int rc = BZ2_bzBuffToBuffCompress(comp, &comp_len,
                                      (char *)msg, in_len, 9, 0, 0);
    assert(rc == BZ_OK);
    assert(comp_len > 0);

    char out[512];
    unsigned int out_len = sizeof(out);
    rc = BZ2_bzBuffToBuffDecompress(out, &out_len, comp, comp_len, 0, 0);
    assert(rc == BZ_OK);
    assert(out_len == in_len);
    assert(memcmp(out, msg, in_len) == 0);
    return 0;
}
