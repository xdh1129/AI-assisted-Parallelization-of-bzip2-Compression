#ifndef BZIP2_HUFFMAN_CUDA_H
#define BZIP2_HUFFMAN_CUDA_H

#include "../bzlib_private.h"

#ifdef __cplusplus
extern "C" {
#endif

Bool BZ2_cudaHuffmanPrepare ( void** workspace, const UInt16* mtfv,
                              Int32 nMTF, Int32 verbosity );
Bool BZ2_cudaHuffmanIterate ( void* workspace,
                              UChar len[BZ_N_GROUPS][BZ_MAX_ALPHA_SIZE],
                              Int32 alphaSize, Int32 nGroups,
                              UChar* selector,
                              Int32 rfreq[BZ_N_GROUPS][BZ_MAX_ALPHA_SIZE],
                              Int32* fave, Int32* totc, Int32 verbosity );
void BZ2_cudaHuffmanCleanup ( void* workspace );

#ifdef __cplusplus
}
#endif

#endif
