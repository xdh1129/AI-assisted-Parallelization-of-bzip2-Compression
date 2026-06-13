#include "huffman_cuda.h"

#include <cuda_runtime.h>
#include <stdio.h>
#include <stdlib.h>

namespace {

const int kThreadsPerBlock = 256;

struct CudaHuffmanWorkspace {
   UInt16* d_mtfv;
   UChar* d_len;
   UChar* d_selector;
   Int32* d_rfreq;
   Int32* d_fave;
   Int32* d_totc;
   size_t mtfvCapacity;
   size_t selectorCapacity;
   Int32 nMTF;
};

__global__
void huffman_group_cost_kernel ( const UInt16* mtfv, Int32 nMTF,
                                 const UChar* len, Int32 nGroups,
                                 UChar* selector, Int32* rfreq,
                                 Int32* fave, Int32* totc )
{
   Int32 group = (Int32)(blockIdx.x * blockDim.x + threadIdx.x);
   Int32 gs = group * BZ_G_SIZE;
   Int32 ge, i, t, bestTable;
   Int32 cost[BZ_N_GROUPS];
   Int32 bestCost;
   if (gs >= nMTF) return;
   ge = gs + BZ_G_SIZE;
   if (ge > nMTF) ge = nMTF;
   for (t = 0; t < nGroups; t++) cost[t] = 0;
   for (i = gs; i < ge; i++) {
      UInt16 symbol = mtfv[i];
      for (t = 0; t < nGroups; t++)
         cost[t] += len[t * BZ_MAX_ALPHA_SIZE + symbol];
   }
   bestTable = 0;
   bestCost = cost[0];
   for (t = 1; t < nGroups; t++)
      if (cost[t] < bestCost) {
         bestCost = cost[t];
         bestTable = t;
      }
   selector[group] = (UChar)bestTable;
   atomicAdd ( &fave[bestTable], 1 );
   atomicAdd ( totc, bestCost );
   for (i = gs; i < ge; i++)
      atomicAdd ( &rfreq[bestTable * BZ_MAX_ALPHA_SIZE + mtfv[i]], 1 );
}

Bool cuda_disabled ( void )
{
   const char* value = getenv ( "BZ2_DISABLE_CUDA" );
   return (value != NULL && value[0] != '\0' && value[0] != '0')
             ? True : False;
}

Bool check_cuda ( cudaError_t status, const char* label, Int32 verbosity )
{
   if (status == cudaSuccess) return True;
   if (verbosity >= 2)
      fprintf ( stderr, "    CUDA Huffman disabled after %s failed: %s\n",
                label, cudaGetErrorString ( status ) );
   return False;
}

void release_workspace ( CudaHuffmanWorkspace* workspace )
{
   if (workspace == NULL) return;
   cudaFree ( workspace->d_totc );
   cudaFree ( workspace->d_fave );
   cudaFree ( workspace->d_rfreq );
   cudaFree ( workspace->d_selector );
   cudaFree ( workspace->d_len );
   cudaFree ( workspace->d_mtfv );
   free ( workspace );
}

Bool ensure_workspace ( void** opaqueWorkspace, Int32 nMTF,
                        Int32 verbosity )
{
   CudaHuffmanWorkspace* workspace;
   size_t selectorCount = (size_t)((nMTF + BZ_G_SIZE - 1) / BZ_G_SIZE);
   Int32 deviceCount = 0;
   if (opaqueWorkspace == NULL || cuda_disabled()) return False;
   if (!check_cuda ( cudaGetDeviceCount ( &deviceCount ),
                     "cudaGetDeviceCount", verbosity ) || deviceCount <= 0)
      return False;
   workspace = (CudaHuffmanWorkspace*)(*opaqueWorkspace);
   if (workspace == NULL) {
      workspace = (CudaHuffmanWorkspace*)calloc ( 1, sizeof(*workspace) );
      if (workspace == NULL) return False;
      *opaqueWorkspace = workspace;
      if (!check_cuda ( cudaMalloc ( (void**)&workspace->d_len,
                                     BZ_N_GROUPS * BZ_MAX_ALPHA_SIZE ),
                        "cudaMalloc(len)", verbosity ) ||
          !check_cuda ( cudaMalloc ( (void**)&workspace->d_rfreq,
                                     BZ_N_GROUPS * BZ_MAX_ALPHA_SIZE *
                                     sizeof(Int32) ),
                        "cudaMalloc(rfreq)", verbosity ) ||
          !check_cuda ( cudaMalloc ( (void**)&workspace->d_fave,
                                     BZ_N_GROUPS * sizeof(Int32) ),
                        "cudaMalloc(fave)", verbosity ) ||
          !check_cuda ( cudaMalloc ( (void**)&workspace->d_totc,
                                     sizeof(Int32) ),
                        "cudaMalloc(totc)", verbosity )) {
         release_workspace ( workspace );
         *opaqueWorkspace = NULL;
         return False;
      }
   }
   if (workspace->mtfvCapacity < (size_t)nMTF) {
      cudaFree ( workspace->d_mtfv );
      workspace->d_mtfv = NULL;
      workspace->mtfvCapacity = 0;
      if (!check_cuda ( cudaMalloc ( (void**)&workspace->d_mtfv,
                                     (size_t)nMTF * sizeof(UInt16) ),
                        "cudaMalloc(mtfv)", verbosity )) return False;
      workspace->mtfvCapacity = (size_t)nMTF;
   }
   if (workspace->selectorCapacity < selectorCount) {
      cudaFree ( workspace->d_selector );
      workspace->d_selector = NULL;
      workspace->selectorCapacity = 0;
      if (!check_cuda ( cudaMalloc ( (void**)&workspace->d_selector,
                                     selectorCount ),
                        "cudaMalloc(selector)", verbosity )) return False;
      workspace->selectorCapacity = selectorCount;
   }
   return True;
}

} /* namespace */

extern "C"
Bool BZ2_cudaHuffmanPrepare ( void** opaqueWorkspace, const UInt16* mtfv,
                              Int32 nMTF, Int32 verbosity )
{
   CudaHuffmanWorkspace* workspace;
   if (mtfv == NULL || nMTF <= 0 ||
       !ensure_workspace ( opaqueWorkspace, nMTF, verbosity )) return False;
   workspace = (CudaHuffmanWorkspace*)(*opaqueWorkspace);
   if (!check_cuda ( cudaMemcpy ( workspace->d_mtfv, mtfv,
                                  (size_t)nMTF * sizeof(UInt16),
                                  cudaMemcpyHostToDevice ),
                     "cudaMemcpy(mtfv)", verbosity )) return False;
   workspace->nMTF = nMTF;
   return True;
}

extern "C"
Bool BZ2_cudaHuffmanIterate ( void* opaqueWorkspace,
                              UChar len[BZ_N_GROUPS][BZ_MAX_ALPHA_SIZE],
                              Int32 alphaSize, Int32 nGroups,
                              UChar* selector,
                              Int32 rfreq[BZ_N_GROUPS][BZ_MAX_ALPHA_SIZE],
                              Int32* fave, Int32* totc, Int32 verbosity )
{
   CudaHuffmanWorkspace* workspace =
      (CudaHuffmanWorkspace*)opaqueWorkspace;
   Int32 nSelectors, blocks;
   size_t rfreqBytes = BZ_N_GROUPS * BZ_MAX_ALPHA_SIZE * sizeof(Int32);
   if (workspace == NULL || alphaSize <= 0 ||
       alphaSize > BZ_MAX_ALPHA_SIZE || nGroups < 2 ||
       nGroups > BZ_N_GROUPS) return False;
   nSelectors = (workspace->nMTF + BZ_G_SIZE - 1) / BZ_G_SIZE;
   blocks = (nSelectors + kThreadsPerBlock - 1) / kThreadsPerBlock;
   if (!check_cuda ( cudaMemcpy ( workspace->d_len, len,
                                  BZ_N_GROUPS * BZ_MAX_ALPHA_SIZE,
                                  cudaMemcpyHostToDevice ),
                     "cudaMemcpy(len)", verbosity ) ||
       !check_cuda ( cudaMemset ( workspace->d_rfreq, 0, rfreqBytes ),
                     "cudaMemset(rfreq)", verbosity ) ||
       !check_cuda ( cudaMemset ( workspace->d_fave, 0,
                                  BZ_N_GROUPS * sizeof(Int32) ),
                     "cudaMemset(fave)", verbosity ) ||
       !check_cuda ( cudaMemset ( workspace->d_totc, 0, sizeof(Int32) ),
                     "cudaMemset(totc)", verbosity )) return False;
   huffman_group_cost_kernel<<<blocks, kThreadsPerBlock>>>
      ( workspace->d_mtfv, workspace->nMTF, workspace->d_len,
        nGroups, workspace->d_selector, workspace->d_rfreq,
        workspace->d_fave, workspace->d_totc );
   if (!check_cuda ( cudaGetLastError (), "huffman_group_cost_kernel",
                     verbosity )) return False;
   if (!check_cuda ( cudaMemcpy ( selector, workspace->d_selector,
                                  (size_t)nSelectors,
                                  cudaMemcpyDeviceToHost ),
                     "cudaMemcpy(selector)", verbosity ) ||
       !check_cuda ( cudaMemcpy ( rfreq, workspace->d_rfreq, rfreqBytes,
                                  cudaMemcpyDeviceToHost ),
                     "cudaMemcpy(rfreq)", verbosity ) ||
       !check_cuda ( cudaMemcpy ( fave, workspace->d_fave,
                                  BZ_N_GROUPS * sizeof(Int32),
                                  cudaMemcpyDeviceToHost ),
                     "cudaMemcpy(fave)", verbosity ) ||
       !check_cuda ( cudaMemcpy ( totc, workspace->d_totc, sizeof(Int32),
                                  cudaMemcpyDeviceToHost ),
                     "cudaMemcpy(totc)", verbosity )) return False;
   return True;
}

extern "C"
void BZ2_cudaHuffmanCleanup ( void* opaqueWorkspace )
{
   release_workspace ( (CudaHuffmanWorkspace*)opaqueWorkspace );
}
