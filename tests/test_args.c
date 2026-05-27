#include <assert.h>
#include <string.h>
#include "../src/args.h"

int main(void) {
    /* full options */
    {
        char *argv[] = {"pbzx","-i","in.txt","-o","out.bz2",
                        "--threads","4","--block-size","1000","--level","5"};
        Options o;
        assert(args_parse(11, argv, &o) == 0);
        assert(o.threads == 4);
        assert(o.block_size == 1000);
        assert(o.level == 5);
        assert(strcmp(o.in_path, "in.txt") == 0);
        assert(strcmp(o.out_path, "out.bz2") == 0);
    }
    /* defaults */
    {
        char *argv[] = {"pbzx","-i","in.txt","-o","out.bz2"};
        Options o;
        assert(args_parse(5, argv, &o) == 0);
        assert(o.threads == 1);
        assert(o.block_size == 900000);
        assert(o.level == 9);
    }
    /* missing -o */
    {
        char *argv[] = {"pbzx","-i","in.txt"};
        Options o;
        assert(args_parse(3, argv, &o) != 0);
    }
    /* invalid block size */
    {
        char *argv[] = {"pbzx","-i","a","-o","b","--block-size","0"};
        Options o;
        assert(args_parse(7, argv, &o) != 0);
    }
    return 0;
}
