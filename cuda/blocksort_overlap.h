#ifndef BZIP2_BLOCKSORT_OVERLAP_H
#define BZIP2_BLOCKSORT_OVERLAP_H

#include "../bzlib_private.h"

void* BZ2_cudaOverlapCreate ( void );

Bool BZ2_cudaOverlapLaunch ( void* worker,
                             UInt32* ptr,
                             UChar* block,
                             Int32 nblock,
                             Int32 verbosity );

Bool BZ2_cudaOverlapWait ( void* worker,
                           Int32* origPtr,
                           double* sortSeconds );

void BZ2_cudaOverlapDestroy ( void* worker );

#endif
