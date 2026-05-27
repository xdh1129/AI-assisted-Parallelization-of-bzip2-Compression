#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "../src/writer.h"

int main(void) {
    CompressedBlock b[3];
    b[0].data = (uint8_t *)"AAA";  b[0].len = 3;
    b[1].data = (uint8_t *)"BB";   b[1].len = 2;
    b[2].data = (uint8_t *)"CCCC"; b[2].len = 4;

    FILE *f = tmpfile();
    assert(f);
    assert(write_blocks_in_order(f, b, 3) == 0);
    rewind(f);

    char buf[16] = {0};
    size_t n = fread(buf, 1, sizeof(buf), f);
    assert(n == 9);
    assert(memcmp(buf, "AAABBCCCC", 9) == 0);
    fclose(f);
    return 0;
}
