#ifndef BZIP2_BLOCKSORT_CUDA_H
#define BZIP2_BLOCKSORT_CUDA_H

#include "../bzlib_private.h"

#ifdef __cplusplus
extern "C" {
#endif

Bool BZ2_cudaBlockSort ( UInt32* ptr, UChar* block, Int32 nblock, Int32 verbosity );

#ifdef __cplusplus
}
#endif

#endif
