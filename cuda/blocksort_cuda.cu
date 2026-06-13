#include "blocksort_cuda.h"

#include <cub/cub.cuh>
#include <cuda_runtime.h>

#include <stdio.h>
#include <stdlib.h>

namespace {

const unsigned int kIndexBits = 21U;
const unsigned long long kIndexMask = (1ULL << kIndexBits) - 1ULL;
const int kThreadsPerBlock = 256;

struct CudaBlockSortWorkspace {
   UChar* d_block;
   UChar* d_bwt;
   UInt32* d_rank_a;
   UInt32* d_rank_b;
   UInt32* d_indices_in;
   UInt32* d_indices_out;
   UInt32* d_flags;
   UInt32* d_rank_by_pos;
   unsigned long long* d_keys_in;
   unsigned long long* d_keys_out;
   void* sort_temp;
   void* scan_temp;
   size_t sort_temp_bytes;
   size_t scan_temp_bytes;
   size_t capacity;
};

__device__ __host__
unsigned long long pack_key ( UInt32 firstRank, UInt32 secondRank, UInt32 index )
{
   return (((unsigned long long)firstRank) << (2U * kIndexBits)) |
          (((unsigned long long)secondRank) << kIndexBits) |
          ((unsigned long long)index);
}

__global__
void init_ranks_kernel ( const UChar* block,
                         UInt32* ranks,
                         UInt32* indices,
                         Int32 nblock )
{
   Int32 i = (Int32)(blockIdx.x * blockDim.x + threadIdx.x);
   if (i >= nblock) return;
   ranks[i] = (UInt32)block[i];
   indices[i] = (UInt32)i;
}

__global__
void build_keys_kernel ( const UInt32* ranks,
                         unsigned long long* keys,
                         Int32 nblock,
                         Int32 step )
{
   Int32 i = (Int32)(blockIdx.x * blockDim.x + threadIdx.x);
   Int32 second;
   if (i >= nblock) return;

   second = i + step;
   if (second >= nblock) second -= nblock;

   keys[i] = pack_key ( ranks[i], ranks[second], (UInt32)i );
}

__global__
void mark_rank_breaks_kernel ( const unsigned long long* sortedKeys,
                               UInt32* flags,
                               Int32 nblock )
{
   Int32 i = (Int32)(blockIdx.x * blockDim.x + threadIdx.x);
   if (i >= nblock) return;

   if (i == 0) {
      flags[i] = 0;
   } else {
      flags[i] = ((sortedKeys[i] >> kIndexBits) !=
                  (sortedKeys[i - 1] >> kIndexBits)) ? 1U : 0U;
   }
}

__global__
void scatter_ranks_kernel ( const UInt32* sortedIndices,
                            const UInt32* sortedRanks,
                            UInt32* ranksOut,
                            Int32 nblock )
{
   Int32 i = (Int32)(blockIdx.x * blockDim.x + threadIdx.x);
   if (i >= nblock) return;
   ranksOut[sortedIndices[i] & (UInt32)kIndexMask] = sortedRanks[i];
}

__global__
void bwt_last_column_kernel ( const UChar* block,
                              const UInt32* sortedIndices,
                              UChar* bwt,
                              Int32 nblock )
{
   Int32 i = (Int32)(blockIdx.x * blockDim.x + threadIdx.x);
   UInt32 blockIndex;
   if (i >= nblock) return;
   blockIndex = sortedIndices[i] & (UInt32)kIndexMask;
   if (blockIndex == 0) blockIndex = (UInt32)nblock;
   bwt[i] = block[blockIndex - 1];
}

Bool cuda_disabled ( void )
{
   const char* disabled = getenv ( "BZ2_DISABLE_CUDA" );
   return (disabled != NULL && disabled[0] != '\0' && disabled[0] != '0')
             ? True : False;
}

Bool check_cuda ( cudaError_t status, const char* label, Int32 verbosity )
{
   if (status == cudaSuccess) return True;

   if (verbosity >= 2)
      fprintf ( stderr, "    CUDA blocksort disabled after %s failed: %s\n",
                label, cudaGetErrorString ( status ) );

   return False;
}

Int32 grid_size ( Int32 nblock )
{
   return (nblock + kThreadsPerBlock - 1) / kThreadsPerBlock;
}

void release_temp_buffers ( CudaBlockSortWorkspace* workspace )
{
   cudaFree ( workspace->scan_temp );
   cudaFree ( workspace->sort_temp );
   workspace->scan_temp = NULL;
   workspace->sort_temp = NULL;
   workspace->scan_temp_bytes = 0;
   workspace->sort_temp_bytes = 0;
}

void release_device_buffers ( CudaBlockSortWorkspace* workspace )
{
   release_temp_buffers ( workspace );
   cudaFree ( workspace->d_keys_out );
   cudaFree ( workspace->d_keys_in );
   cudaFree ( workspace->d_rank_by_pos );
   cudaFree ( workspace->d_flags );
   cudaFree ( workspace->d_indices_out );
   cudaFree ( workspace->d_indices_in );
   cudaFree ( workspace->d_rank_b );
   cudaFree ( workspace->d_rank_a );
   cudaFree ( workspace->d_block );
   cudaFree ( workspace->d_bwt );

   workspace->d_keys_out = NULL;
   workspace->d_keys_in = NULL;
   workspace->d_rank_by_pos = NULL;
   workspace->d_flags = NULL;
   workspace->d_indices_out = NULL;
   workspace->d_indices_in = NULL;
   workspace->d_rank_b = NULL;
   workspace->d_rank_a = NULL;
   workspace->d_block = NULL;
   workspace->d_bwt = NULL;
   workspace->capacity = 0;
}

Bool allocate_device_buffers ( CudaBlockSortWorkspace* workspace,
                               Int32 nblock,
                               Int32 verbosity )
{
   size_t uchar_bytes = (size_t)nblock * sizeof(UChar);
   size_t uint_bytes = (size_t)nblock * sizeof(UInt32);
   size_t key_bytes = (size_t)nblock * sizeof(unsigned long long);

   if (!check_cuda ( cudaMalloc ( (void**)&workspace->d_block, uchar_bytes ),
                     "cudaMalloc(block)", verbosity )) return False;
   if (!check_cuda ( cudaMalloc ( (void**)&workspace->d_rank_a, uint_bytes ),
                     "cudaMalloc(rank_a)", verbosity )) return False;
   if (!check_cuda ( cudaMalloc ( (void**)&workspace->d_rank_b, uint_bytes ),
                     "cudaMalloc(rank_b)", verbosity )) return False;
   if (!check_cuda ( cudaMalloc ( (void**)&workspace->d_indices_in, uint_bytes ),
                     "cudaMalloc(indices_in)", verbosity )) return False;
   if (!check_cuda ( cudaMalloc ( (void**)&workspace->d_indices_out, uint_bytes ),
                     "cudaMalloc(indices_out)", verbosity )) return False;
   if (!check_cuda ( cudaMalloc ( (void**)&workspace->d_flags, uint_bytes ),
                     "cudaMalloc(flags)", verbosity )) return False;
   if (!check_cuda ( cudaMalloc ( (void**)&workspace->d_rank_by_pos, uint_bytes ),
                     "cudaMalloc(rank_by_pos)", verbosity )) return False;
   if (!check_cuda ( cudaMalloc ( (void**)&workspace->d_keys_in, key_bytes ),
                     "cudaMalloc(keys_in)", verbosity )) return False;
   if (!check_cuda ( cudaMalloc ( (void**)&workspace->d_keys_out, key_bytes ),
                     "cudaMalloc(keys_out)", verbosity )) return False;

   workspace->capacity = (size_t)nblock;
   return True;
}

Bool ensure_workspace_capacity ( void** opaqueWorkspace,
                                 Int32 nblock,
                                 Int32 verbosity )
{
   CudaBlockSortWorkspace* workspace;

   if (opaqueWorkspace == NULL) return False;

   workspace = (CudaBlockSortWorkspace*)(*opaqueWorkspace);
   if (workspace == NULL) {
      workspace = (CudaBlockSortWorkspace*)calloc ( 1, sizeof(CudaBlockSortWorkspace) );
      if (workspace == NULL) return False;
      *opaqueWorkspace = workspace;
   }

   if (workspace->capacity >= (size_t)nblock) return True;

   release_device_buffers ( workspace );
   if (!allocate_device_buffers ( workspace, nblock, verbosity )) {
      release_device_buffers ( workspace );
      return False;
   }

   if (verbosity >= 3)
      fprintf ( stderr, "      CUDA blocksort workspace capacity is %d bytes\n",
                nblock );

   return True;
}

Bool ensure_temp_capacity ( CudaBlockSortWorkspace* workspace,
                            Int32 nblock,
                            Int32 verbosity )
{
   size_t required_sort_temp_bytes = 0;
   size_t required_scan_temp_bytes = 0;

   if (!check_cuda (
          cub::DeviceRadixSort::SortPairs ( NULL, required_sort_temp_bytes,
                                            workspace->d_keys_in,
                                            workspace->d_keys_out,
                                            workspace->d_indices_in,
                                            workspace->d_indices_out,
                                            nblock, 0, 64 ),
          "cub::DeviceRadixSort::SortPairs(size)", verbosity ))
      return False;
   if (!check_cuda (
          cub::DeviceScan::InclusiveSum ( NULL, required_scan_temp_bytes,
                                          workspace->d_flags,
                                          workspace->d_rank_by_pos,
                                          nblock ),
          "cub::DeviceScan::InclusiveSum(size)", verbosity ))
      return False;

   if (workspace->sort_temp_bytes < required_sort_temp_bytes) {
      cudaFree ( workspace->sort_temp );
      workspace->sort_temp = NULL;
      workspace->sort_temp_bytes = 0;
      if (!check_cuda ( cudaMalloc ( &workspace->sort_temp,
                                     required_sort_temp_bytes ),
                        "cudaMalloc(sort_temp)", verbosity ))
         return False;
      workspace->sort_temp_bytes = required_sort_temp_bytes;
   }

   if (workspace->scan_temp_bytes < required_scan_temp_bytes) {
      cudaFree ( workspace->scan_temp );
      workspace->scan_temp = NULL;
      workspace->scan_temp_bytes = 0;
      if (!check_cuda ( cudaMalloc ( &workspace->scan_temp,
                                     required_scan_temp_bytes ),
                        "cudaMalloc(scan_temp)", verbosity ))
         return False;
      workspace->scan_temp_bytes = required_scan_temp_bytes;
   }

   return True;
}

} /* namespace */

extern "C"
Bool BZ2_cudaBlockSort ( void** opaqueWorkspace,
                         UInt32* ptr,
                         UChar* block,
                         UChar* bwt,
                         Int32 nblock,
                         Int32 verbosity )
{
   CudaBlockSortWorkspace* workspace;
   UInt32 max_rank = 0;
   Int32 device_count = 0;
   Int32 blocks = grid_size ( nblock );
   Int32 step;

   if (ptr == NULL || block == NULL || nblock <= 0) return False;
   if (nblock >= (Int32)(1U << kIndexBits)) return False;
   if (cuda_disabled ()) {
      if (verbosity >= 3)
         fprintf ( stderr, "      CUDA blocksort disabled by BZ2_DISABLE_CUDA\n" );
      return False;
   }

   if (!check_cuda ( cudaGetDeviceCount ( &device_count ),
                     "cudaGetDeviceCount", verbosity ))
      return False;
   if (device_count <= 0) return False;

   if (!ensure_workspace_capacity ( opaqueWorkspace, nblock, verbosity ))
      return False;
   workspace = (CudaBlockSortWorkspace*)(*opaqueWorkspace);

   if (!check_cuda ( cudaMemcpy ( workspace->d_block, block,
                                  (size_t)nblock * sizeof(UChar),
                                  cudaMemcpyHostToDevice ),
                     "cudaMemcpy(block)", verbosity )) return False;

   init_ranks_kernel<<<blocks, kThreadsPerBlock>>>
      ( workspace->d_block, workspace->d_rank_a, workspace->d_indices_in, nblock );
   if (!check_cuda ( cudaGetLastError (), "init_ranks_kernel", verbosity ))
      return False;

   if (!ensure_temp_capacity ( workspace, nblock, verbosity ))
      return False;

   for (step = 1; step < nblock; step <<= 1) {
      build_keys_kernel<<<blocks, kThreadsPerBlock>>>
         ( workspace->d_rank_a, workspace->d_keys_in, nblock, step );
      if (!check_cuda ( cudaGetLastError (), "build_keys_kernel", verbosity ))
         return False;

      if (!check_cuda (
             cub::DeviceRadixSort::SortPairs ( workspace->sort_temp,
                                               workspace->sort_temp_bytes,
                                               workspace->d_keys_in,
                                               workspace->d_keys_out,
                                               workspace->d_indices_in,
                                               workspace->d_indices_out,
                                               nblock, 0, 64 ),
             "cub::DeviceRadixSort::SortPairs", verbosity ))
         return False;

      mark_rank_breaks_kernel<<<blocks, kThreadsPerBlock>>>
         ( workspace->d_keys_out, workspace->d_flags, nblock );
      if (!check_cuda ( cudaGetLastError (), "mark_rank_breaks_kernel", verbosity ))
         return False;

      if (!check_cuda (
             cub::DeviceScan::InclusiveSum ( workspace->scan_temp,
                                             workspace->scan_temp_bytes,
                                             workspace->d_flags,
                                             workspace->d_rank_by_pos,
                                             nblock ),
             "cub::DeviceScan::InclusiveSum", verbosity ))
         return False;

      scatter_ranks_kernel<<<blocks, kThreadsPerBlock>>>
         ( workspace->d_indices_out, workspace->d_rank_by_pos,
           workspace->d_rank_b, nblock );
      if (!check_cuda ( cudaGetLastError (), "scatter_ranks_kernel", verbosity ))
         return False;

      if (!check_cuda ( cudaMemcpy ( &max_rank,
                                     workspace->d_rank_by_pos + nblock - 1,
                                     sizeof(UInt32), cudaMemcpyDeviceToHost ),
                        "cudaMemcpy(max_rank)", verbosity ))
         return False;

      {
         UInt32* tmp = workspace->d_rank_a;
         workspace->d_rank_a = workspace->d_rank_b;
         workspace->d_rank_b = tmp;
      }

      if (max_rank == (UInt32)(nblock - 1)) break;
      if (step > nblock / 2) break;
   }

   if (!check_cuda ( cudaMemcpy ( ptr, workspace->d_indices_out,
                                  (size_t)nblock * sizeof(UInt32),
                                  cudaMemcpyDeviceToHost ),
                     "cudaMemcpy(ptr)", verbosity ))
      return False;

   if (bwt != NULL) {
      if (workspace->d_bwt == NULL &&
          !check_cuda ( cudaMalloc ( (void**)&workspace->d_bwt,
                                     workspace->capacity * sizeof(UChar) ),
                        "cudaMalloc(bwt)", verbosity )) return False;
      bwt_last_column_kernel<<<blocks, kThreadsPerBlock>>>
         ( workspace->d_block, workspace->d_indices_out,
           workspace->d_bwt, nblock );
      if (!check_cuda ( cudaGetLastError (), "bwt_last_column_kernel",
                        verbosity )) return False;
      if (!check_cuda ( cudaMemcpy ( bwt, workspace->d_bwt,
                                     (size_t)nblock * sizeof(UChar),
                                     cudaMemcpyDeviceToHost ),
                        "cudaMemcpy(bwt)", verbosity )) return False;
   }

   return True;
}

extern "C"
void BZ2_cudaBlockSortCleanup ( void* opaqueWorkspace )
{
   CudaBlockSortWorkspace* workspace =
      (CudaBlockSortWorkspace*)opaqueWorkspace;

   if (workspace == NULL) return;
   release_device_buffers ( workspace );
   free ( workspace );
}
