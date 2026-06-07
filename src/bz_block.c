#include "bz_block.h"
#include <stdlib.h>
#include <bzlib.h>

/* Per-thread reusable workspace arena.
 *
 * BZ2_bzBuffToBuffCompress() mallocs ~7.6 MB of BWT workspace per call and frees
 * it on return. Profiling the parallel build (perf: ~674K page-faults; strace:
 * madvise/munmap/mmap dominating) showed glibc serving those large allocations
 * via mmap, so every block faulted in fresh zero pages and unmapped them again.
 *
 * We instead drive bzip2's low-level streaming API with a custom allocator that
 * hands workspace out of a thread-local buffer allocated once and reused across
 * every block that thread compresses. bzfree is a no-op for arena-owned memory,
 * and the arena is reset at the start of each block (each block fully releases
 * its workspace via BZ2_bzCompressEnd before the next begins on the same thread).
 *
 * bzip2's largest single allocation at level 9 is arr2 = (900000+34)*4 ≈ 3.6 MB;
 * total workspace is ~7.5 MB. A 16 MB arena covers any level with headroom. Any
 * request the arena cannot satisfy falls back to malloc, and bzfree frees only
 * pointers that lie outside the arena, so correctness never depends on sizing. */
typedef struct {
    unsigned char *base;
    size_t cap;
    size_t used;
} Arena;

static _Thread_local Arena g_arena;

#define ARENA_CAP (16u << 20)

static void *arena_alloc(void *opaque, int n, int m) {
    (void)opaque;
    size_t bytes = (size_t)n * (size_t)m;
    bytes = (bytes + 15u) & ~(size_t)15u;  /* 16-byte align each chunk */

    Arena *a = &g_arena;
    if (!a->base) {
        a->base = (unsigned char *)malloc(ARENA_CAP);
        a->cap = a->base ? ARENA_CAP : 0;
        a->used = 0;
    }
    if (a->base && a->used + bytes <= a->cap) {
        void *p = a->base + a->used;
        a->used += bytes;
        return p;
    }
    return malloc(bytes);  /* fallback: arena absent or exhausted */
}

static void arena_free(void *opaque, void *p) {
    (void)opaque;
    if (!p) return;
    Arena *a = &g_arena;
    if (a->base && (unsigned char *)p >= a->base &&
        (unsigned char *)p < a->base + a->cap)
        return;  /* arena-owned: reclaimed in bulk by the reset below */
    free(p);
}

int compress_block(const uint8_t *in, size_t in_len, int level,
                   uint8_t **out, size_t *out_len) {
    /* bzip2 worst-case output: in_len + in_len/100 + 600 */
    unsigned int dest_len = (unsigned int)(in_len + in_len / 100 + 600);
    uint8_t *buf = (uint8_t *)malloc(dest_len);
    if (!buf) return 1;

    static uint8_t empty[1] = {0};
    char *src = (char *)(in_len ? (const char *)in : (const char *)empty);

    /* Reset this thread's arena: the previous block on this thread has already
     * run BZ2_bzCompressEnd, so all its workspace is free to reuse. */
    g_arena.used = 0;

    bz_stream strm;
    strm.bzalloc = arena_alloc;
    strm.bzfree = arena_free;
    strm.opaque = NULL;

    if (BZ2_bzCompressInit(&strm, level, 0, 0) != BZ_OK) { free(buf); return 1; }

    strm.next_in = src;
    strm.avail_in = (unsigned int)in_len;
    strm.next_out = (char *)buf;
    strm.avail_out = dest_len;

    int rc;
    do {
        rc = BZ2_bzCompress(&strm, BZ_FINISH);
    } while (rc == BZ_FINISH_OK);

    if (rc != BZ_STREAM_END) {
        BZ2_bzCompressEnd(&strm);
        free(buf);
        return 1;
    }

    *out_len = dest_len - strm.avail_out;
    BZ2_bzCompressEnd(&strm);

    *out = buf;
    return 0;
}
