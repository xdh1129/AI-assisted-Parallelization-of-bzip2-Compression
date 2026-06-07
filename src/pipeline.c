#define _POSIX_C_SOURCE 200809L
#include "pipeline.h"
#include "bz_block.h"
#include <stdlib.h>
#include <stdint.h>
#include <pthread.h>

/* One in-flight block. Indexed in `slots` by (id % qdepth).
 *
 * Backpressure keeps the live id window strictly smaller than qdepth
 * (the reader blocks once read_count - next_write == qdepth), so the ids of
 * all in-flight blocks are distinct modulo qdepth and never collide here. */
typedef struct {
    uint8_t *raw;       /* input bytes; freed once compressed                 */
    size_t   raw_len;
    uint8_t *comp;      /* compressed .bz2 stream; freed once written         */
    size_t   comp_len;
    uint32_t id;
    int      done;      /* 1 = compressed and ready for the writer            */
} Slot;

typedef struct {
    FILE  *in, *out;
    int    level;
    size_t block_size;
    size_t qdepth;

    pthread_mutex_t mtx;
    pthread_cond_t  cv_reader;   /* reader waits while the id window is full   */
    pthread_cond_t  cv_worker;   /* workers wait while no block is queued      */
    pthread_cond_t  cv_writer;   /* writer waits for the next id to be done    */

    Slot  *slots;                /* qdepth entries                            */
    int   *workq;                /* ring of slot indices awaiting compression */
    size_t wq_head, wq_tail, wq_count;

    size_t read_count;           /* ids assigned by the reader so far         */
    size_t next_write;           /* next id the writer will emit              */
    size_t total;                /* valid once `closed` is set                */
    int    closed;               /* reader hit EOF                            */
    int    err;                  /* sticky failure flag                       */

    size_t input_bytes;
    size_t output_bytes;
} Pipeline;

/* Wake everyone so blocked threads re-check `err` and unwind. Caller holds mtx. */
static void fail(Pipeline *p) {
    p->err = 1;
    pthread_cond_broadcast(&p->cv_reader);
    pthread_cond_broadcast(&p->cv_worker);
    pthread_cond_broadcast(&p->cv_writer);
}

static void *worker_main(void *arg) {
    Pipeline *p = (Pipeline *)arg;
    for (;;) {
        pthread_mutex_lock(&p->mtx);
        while (p->wq_count == 0 && !p->closed && !p->err)
            pthread_cond_wait(&p->cv_worker, &p->mtx);
        if (p->err || (p->wq_count == 0 && p->closed)) {
            pthread_mutex_unlock(&p->mtx);
            break;
        }
        int idx = p->workq[p->wq_head];
        p->wq_head = (p->wq_head + 1) % p->qdepth;
        p->wq_count--;
        uint8_t *raw = p->slots[idx].raw;
        size_t   raw_len = p->slots[idx].raw_len;
        pthread_mutex_unlock(&p->mtx);

        /* Compress without holding the lock: this is the parallel hot path. */
        uint8_t *out = NULL; size_t out_len = 0;
        int rc = compress_block(raw, raw_len, p->level, &out, &out_len);
        free(raw);

        pthread_mutex_lock(&p->mtx);
        p->slots[idx].raw = NULL;
        if (rc != 0) {
            fail(p);
            pthread_mutex_unlock(&p->mtx);
            break;
        }
        p->slots[idx].comp = out;
        p->slots[idx].comp_len = out_len;
        p->slots[idx].done = 1;
        pthread_cond_signal(&p->cv_writer);
        pthread_mutex_unlock(&p->mtx);
    }
    return NULL;
}

static void *writer_main(void *arg) {
    Pipeline *p = (Pipeline *)arg;
    for (;;) {
        pthread_mutex_lock(&p->mtx);
        while (!p->err
               && !(p->closed && p->next_write == p->total)
               && !p->slots[p->next_write % p->qdepth].done)
            pthread_cond_wait(&p->cv_writer, &p->mtx);
        if (p->err) { pthread_mutex_unlock(&p->mtx); break; }
        if (p->closed && p->next_write == p->total) {
            pthread_mutex_unlock(&p->mtx);
            break;
        }
        int idx = p->next_write % p->qdepth;
        uint8_t *data = p->slots[idx].comp;
        size_t   len  = p->slots[idx].comp_len;
        pthread_mutex_unlock(&p->mtx);

        size_t w = len ? fwrite(data, 1, len, p->out) : 0;
        free(data);

        pthread_mutex_lock(&p->mtx);
        p->slots[idx].comp = NULL;
        p->slots[idx].done = 0;
        if (len && w != len) {            /* short write -> I/O error */
            fail(p);
            pthread_mutex_unlock(&p->mtx);
            break;
        }
        p->output_bytes += len;
        p->next_write++;
        pthread_cond_signal(&p->cv_reader);   /* a slot just freed up */
        pthread_mutex_unlock(&p->mtx);
    }
    return NULL;
}

/* bzip2 of an empty input is a fixed ~14-byte stream; emit one so that empty
 * files still round-trip through bunzip2. */
static int write_empty_stream(Pipeline *p) {
    uint8_t *out = NULL; size_t out_len = 0;
    if (compress_block(NULL, 0, p->level, &out, &out_len) != 0) return 1;
    size_t w = fwrite(out, 1, out_len, p->out);
    free(out);
    if (w != out_len) return 1;
    p->output_bytes += out_len;
    return 0;
}

int pipeline_run(FILE *in, FILE *out, int threads, size_t block_size,
                 int level, size_t qdepth,
                 size_t *out_input_bytes, size_t *out_output_bytes) {
    if (threads < 1) threads = 1;
    if (qdepth < (size_t)threads + 1) qdepth = (size_t)threads + 1;

    Pipeline p = {0};
    p.in = in; p.out = out; p.level = level;
    p.block_size = block_size; p.qdepth = qdepth;
    pthread_mutex_init(&p.mtx, NULL);
    pthread_cond_init(&p.cv_reader, NULL);
    pthread_cond_init(&p.cv_worker, NULL);
    pthread_cond_init(&p.cv_writer, NULL);

    p.slots = (Slot *)calloc(qdepth, sizeof(Slot));
    p.workq = (int  *)malloc(qdepth * sizeof(int));
    pthread_t *wk = (pthread_t *)malloc((size_t)threads * sizeof(pthread_t));
    pthread_t writer;
    if (!p.slots || !p.workq || !wk) {
        free(p.slots); free(p.workq); free(wk);
        return 1;
    }

    int nstarted = 0, writer_started = 0;
    for (int i = 0; i < threads; i++) {
        if (pthread_create(&wk[i], NULL, worker_main, &p) != 0) break;
        nstarted++;
    }
    if (nstarted == threads &&
        pthread_create(&writer, NULL, writer_main, &p) == 0) {
        writer_started = 1;
    } else {
        pthread_mutex_lock(&p.mtx);
        fail(&p);
        pthread_mutex_unlock(&p.mtx);
    }

    /* Reader runs on the calling thread. */
    while (writer_started) {
        uint8_t *buf = (uint8_t *)malloc(block_size);
        if (!buf) { pthread_mutex_lock(&p.mtx); fail(&p); pthread_mutex_unlock(&p.mtx); break; }
        size_t n = fread(buf, 1, block_size, in);
        if (n == 0) {                       /* clean EOF or read error */
            free(buf);
            int ioerr = ferror(in);
            pthread_mutex_lock(&p.mtx);
            if (ioerr) p.err = 1;
            p.closed = 1;
            p.total = p.read_count;
            pthread_cond_broadcast(&p.cv_worker);
            pthread_cond_broadcast(&p.cv_writer);
            pthread_mutex_unlock(&p.mtx);
            break;
        }
        pthread_mutex_lock(&p.mtx);
        while (!p.err && (p.read_count - p.next_write) == qdepth)
            pthread_cond_wait(&p.cv_reader, &p.mtx);
        if (p.err) { pthread_mutex_unlock(&p.mtx); free(buf); break; }
        int idx = (int)(p.read_count % qdepth);
        p.slots[idx].raw = buf;
        p.slots[idx].raw_len = n;
        p.slots[idx].id = (uint32_t)p.read_count;
        p.slots[idx].comp = NULL;
        p.slots[idx].done = 0;
        p.workq[p.wq_tail] = idx;
        p.wq_tail = (p.wq_tail + 1) % qdepth;
        p.wq_count++;
        p.read_count++;
        p.input_bytes += n;
        pthread_cond_signal(&p.cv_worker);
        pthread_mutex_unlock(&p.mtx);
    }

    for (int i = 0; i < nstarted; i++) pthread_join(wk[i], NULL);
    if (writer_started) pthread_join(writer, NULL);

    int rc = p.err ? 1 : 0;

    /* Empty input: emit a single empty .bz2 stream so it still round-trips. */
    if (!rc && p.read_count == 0)
        rc = write_empty_stream(&p);

    /* Reclaim anything left dangling on the error path. */
    for (size_t i = 0; i < qdepth; i++) {
        free(p.slots[i].raw);
        free(p.slots[i].comp);
    }
    free(p.slots); free(p.workq); free(wk);
    pthread_mutex_destroy(&p.mtx);
    pthread_cond_destroy(&p.cv_reader);
    pthread_cond_destroy(&p.cv_worker);
    pthread_cond_destroy(&p.cv_writer);

    if (out_input_bytes)  *out_input_bytes  = p.input_bytes;
    if (out_output_bytes) *out_output_bytes = p.output_bytes;
    return rc;
}
