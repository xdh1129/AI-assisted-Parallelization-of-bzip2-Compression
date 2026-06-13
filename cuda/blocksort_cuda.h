#ifndef BZIP2_BLOCKSORT_CUDA_H
#define BZIP2_BLOCKSORT_CUDA_H

#include "../bzlib_private.h"

#ifdef __cplusplus
extern "C" {
#endif

Bool BZ2_cudaBlockSort ( void** workspace,
                         UInt32* ptr,
                         UChar* block,
                         UChar* bwt,
                         Int32 nblock,
                         Int32 verbosity );

void BZ2_cudaBlockSortCleanup ( void* workspace );

#ifdef __cplusplus
}
#endif

#endif
