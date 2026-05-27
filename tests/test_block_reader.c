#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "../src/block_reader.h"

static FILE *tmpfile_with(const char *content, size_t len) {
    FILE *f = tmpfile();
    assert(f);
    if (len) assert(fwrite(content, 1, len, f) == len);
    rewind(f);
    return f;
}

int main(void) {
    /* 10 bytes, block_size 4 => 4,4,2 */
    {
        FILE *f = tmpfile_with("0123456789", 10);
        Block *b; size_t c;
        assert(read_all_blocks(f, 4, &b, &c) == 0);
        assert(c == 3);
        assert(b[0].len == 4 && b[0].id == 0);
        assert(b[1].len == 4 && b[1].id == 1);
        assert(b[2].len == 2 && b[2].id == 2);
        assert(memcmp(b[0].data, "0123", 4) == 0);
        assert(memcmp(b[2].data, "89", 2) == 0);
        free_blocks(b, c);
        fclose(f);
    }
    /* empty => 0 blocks */
    {
        FILE *f = tmpfile_with("", 0);
        Block *b; size_t c;
        assert(read_all_blocks(f, 4, &b, &c) == 0);
        assert(c == 0);
        free_blocks(b, c);
        fclose(f);
    }
    /* smaller than one block => 1 block */
    {
        FILE *f = tmpfile_with("ab", 2);
        Block *b; size_t c;
        assert(read_all_blocks(f, 100, &b, &c) == 0);
        assert(c == 1 && b[0].len == 2);
        free_blocks(b, c);
        fclose(f);
    }
    return 0;
}
