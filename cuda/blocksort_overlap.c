#include "blocksort_overlap.h"
#include "blocksort_cuda.h"

#include <pthread.h>
#include <stdlib.h>
#include <time.h>

typedef struct {
   pthread_t thread;
   Bool running;
   Bool success;
   UInt32* ptr;
   UChar* block;
   UChar* bwt;
   Int32 nblock;
   Int32 verbosity;
   Int32 origPtr;
   double sortSeconds;
   void* cudaWorkspace;
} BZ2CudaOverlapWorker;

static double overlap_now ( void )
{
   struct timespec ts;
   if (clock_gettime ( CLOCK_MONOTONIC, &ts ) != 0) return 0.0;
   return (double)ts.tv_sec + ((double)ts.tv_nsec / 1000000000.0);
}

static void* overlap_sort_thread ( void* opaque )
{
   BZ2CudaOverlapWorker* worker = (BZ2CudaOverlapWorker*)opaque;
   Int32 i;
   double start = overlap_now();

   worker->success = BZ2_cudaBlockSort ( &worker->cudaWorkspace,
                                         worker->ptr,
                                         worker->block,
                                         worker->bwt,
                                         worker->nblock,
                                         worker->verbosity );
   worker->origPtr = -1;
   if (worker->success) {
      for (i = 0; i < worker->nblock; i++) {
         if (worker->ptr[i] == 0) {
            worker->origPtr = i;
            break;
         }
      }
      if (worker->origPtr < 0) worker->success = False;
   }
   worker->sortSeconds = overlap_now() - start;
   return NULL;
}

void* BZ2_cudaOverlapCreate ( void )
{
   return calloc ( 1, sizeof(BZ2CudaOverlapWorker) );
}

Bool BZ2_cudaOverlapLaunch ( void* opaque,
                             UInt32* ptr,
                             UChar* block,
                             UChar* bwt,
                             Int32 nblock,
                             Int32 verbosity )
{
   BZ2CudaOverlapWorker* worker = (BZ2CudaOverlapWorker*)opaque;
   if (worker == NULL || worker->running || ptr == NULL ||
       block == NULL || nblock < 10000) return False;

   worker->ptr = ptr;
   worker->block = block;
   worker->bwt = bwt;
   worker->nblock = nblock;
   worker->verbosity = verbosity;
   worker->success = False;
   worker->running = True;
   if (pthread_create ( &worker->thread, NULL,
                        overlap_sort_thread, worker ) != 0) {
      worker->running = False;
      return False;
   }
   return True;
}

Bool BZ2_cudaOverlapWait ( void* opaque,
                           Int32* origPtr,
                           double* sortSeconds )
{
   BZ2CudaOverlapWorker* worker = (BZ2CudaOverlapWorker*)opaque;
   if (worker == NULL || !worker->running) return False;
   if (pthread_join ( worker->thread, NULL ) != 0) return False;
   worker->running = False;
   if (origPtr != NULL) *origPtr = worker->origPtr;
   if (sortSeconds != NULL) *sortSeconds = worker->sortSeconds;
   return worker->success;
}

void BZ2_cudaOverlapDestroy ( void* opaque )
{
   BZ2CudaOverlapWorker* worker = (BZ2CudaOverlapWorker*)opaque;
   if (worker == NULL) return;
   if (worker->running) pthread_join ( worker->thread, NULL );
   BZ2_cudaBlockSortCleanup ( worker->cudaWorkspace );
   free ( worker );
}
