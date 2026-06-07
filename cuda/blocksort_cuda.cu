#include "blocksort_cuda.h"

#include <cub/cub.cuh>
#include <cuda_runtime.h>

#include <stdio.h>
#include <stdlib.h>

namespace {

const unsigned int kIndexBits = 21U;
const unsigned long long kIndexMask = (1ULL << kIndexBits) - 1ULL;
const int kThreadsPerBlock = 256;

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

} /* namespace */

extern "C"
Bool BZ2_cudaBlockSort ( UInt32* ptr, UChar* block, Int32 nblock, Int32 verbosity )
{
   UChar* d_block = NULL;
   UInt32* d_rank_a = NULL;
   UInt32* d_rank_b = NULL;
   UInt32* d_indices_in = NULL;
   UInt32* d_indices_out = NULL;
   UInt32* d_flags = NULL;
   UInt32* d_rank_by_pos = NULL;
   unsigned long long* d_keys_in = NULL;
   unsigned long long* d_keys_out = NULL;
   void* sort_temp = NULL;
   void* scan_temp = NULL;
   size_t sort_temp_bytes = 0;
   size_t scan_temp_bytes = 0;
   UInt32 max_rank = 0;
   Int32 device_count = 0;
   Int32 blocks = grid_size ( nblock );
   Int32 step;
   Bool ok = False;

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

   if (!check_cuda ( cudaMalloc ( (void**)&d_block, (size_t)nblock * sizeof(UChar) ),
                     "cudaMalloc(block)", verbosity )) goto cleanup;
   if (!check_cuda ( cudaMalloc ( (void**)&d_rank_a, (size_t)nblock * sizeof(UInt32) ),
                     "cudaMalloc(rank_a)", verbosity )) goto cleanup;
   if (!check_cuda ( cudaMalloc ( (void**)&d_rank_b, (size_t)nblock * sizeof(UInt32) ),
                     "cudaMalloc(rank_b)", verbosity )) goto cleanup;
   if (!check_cuda ( cudaMalloc ( (void**)&d_indices_in, (size_t)nblock * sizeof(UInt32) ),
                     "cudaMalloc(indices_in)", verbosity )) goto cleanup;
   if (!check_cuda ( cudaMalloc ( (void**)&d_indices_out, (size_t)nblock * sizeof(UInt32) ),
                     "cudaMalloc(indices_out)", verbosity )) goto cleanup;
   if (!check_cuda ( cudaMalloc ( (void**)&d_flags, (size_t)nblock * sizeof(UInt32) ),
                     "cudaMalloc(flags)", verbosity )) goto cleanup;
   if (!check_cuda ( cudaMalloc ( (void**)&d_rank_by_pos, (size_t)nblock * sizeof(UInt32) ),
                     "cudaMalloc(rank_by_pos)", verbosity )) goto cleanup;
   if (!check_cuda ( cudaMalloc ( (void**)&d_keys_in,
                                  (size_t)nblock * sizeof(unsigned long long) ),
                     "cudaMalloc(keys_in)", verbosity )) goto cleanup;
   if (!check_cuda ( cudaMalloc ( (void**)&d_keys_out,
                                  (size_t)nblock * sizeof(unsigned long long) ),
                     "cudaMalloc(keys_out)", verbosity )) goto cleanup;

   if (!check_cuda ( cudaMemcpy ( d_block, block, (size_t)nblock * sizeof(UChar),
                                  cudaMemcpyHostToDevice ),
                     "cudaMemcpy(block)", verbosity )) goto cleanup;

   init_ranks_kernel<<<blocks, kThreadsPerBlock>>>
      ( d_block, d_rank_a, d_indices_in, nblock );
   if (!check_cuda ( cudaGetLastError (), "init_ranks_kernel", verbosity ))
      goto cleanup;

   if (!check_cuda (
          cub::DeviceRadixSort::SortPairs ( NULL, sort_temp_bytes,
                                            d_keys_in, d_keys_out,
                                            d_indices_in, d_indices_out,
                                            nblock, 0, 64 ),
          "cub::DeviceRadixSort::SortPairs(size)", verbosity ))
      goto cleanup;
   if (!check_cuda (
          cub::DeviceScan::InclusiveSum ( NULL, scan_temp_bytes,
                                          d_flags, d_rank_by_pos, nblock ),
          "cub::DeviceScan::InclusiveSum(size)", verbosity ))
      goto cleanup;

   if (!check_cuda ( cudaMalloc ( &sort_temp, sort_temp_bytes ),
                     "cudaMalloc(sort_temp)", verbosity )) goto cleanup;
   if (!check_cuda ( cudaMalloc ( &scan_temp, scan_temp_bytes ),
                     "cudaMalloc(scan_temp)", verbosity )) goto cleanup;

   for (step = 1; step < nblock; step <<= 1) {
      build_keys_kernel<<<blocks, kThreadsPerBlock>>>
         ( d_rank_a, d_keys_in, nblock, step );
      if (!check_cuda ( cudaGetLastError (), "build_keys_kernel", verbosity ))
         goto cleanup;

      if (!check_cuda (
             cub::DeviceRadixSort::SortPairs ( sort_temp, sort_temp_bytes,
                                               d_keys_in, d_keys_out,
                                               d_indices_in, d_indices_out,
                                               nblock, 0, 64 ),
             "cub::DeviceRadixSort::SortPairs", verbosity ))
         goto cleanup;

      mark_rank_breaks_kernel<<<blocks, kThreadsPerBlock>>>
         ( d_keys_out, d_flags, nblock );
      if (!check_cuda ( cudaGetLastError (), "mark_rank_breaks_kernel", verbosity ))
         goto cleanup;

      if (!check_cuda (
             cub::DeviceScan::InclusiveSum ( scan_temp, scan_temp_bytes,
                                             d_flags, d_rank_by_pos, nblock ),
             "cub::DeviceScan::InclusiveSum", verbosity ))
         goto cleanup;

      scatter_ranks_kernel<<<blocks, kThreadsPerBlock>>>
         ( d_indices_out, d_rank_by_pos, d_rank_b, nblock );
      if (!check_cuda ( cudaGetLastError (), "scatter_ranks_kernel", verbosity ))
         goto cleanup;

      if (!check_cuda ( cudaMemcpy ( &max_rank, d_rank_by_pos + nblock - 1,
                                     sizeof(UInt32), cudaMemcpyDeviceToHost ),
                        "cudaMemcpy(max_rank)", verbosity ))
         goto cleanup;

      {
         UInt32* tmp = d_rank_a;
         d_rank_a = d_rank_b;
         d_rank_b = tmp;
      }

      if (max_rank == (UInt32)(nblock - 1)) break;
      if (step > nblock / 2) break;
   }

   if (!check_cuda ( cudaMemcpy ( ptr, d_indices_out,
                                  (size_t)nblock * sizeof(UInt32),
                                  cudaMemcpyDeviceToHost ),
                     "cudaMemcpy(ptr)", verbosity )) goto cleanup;

   ok = True;

cleanup:
   cudaFree ( scan_temp );
   cudaFree ( sort_temp );
   cudaFree ( d_keys_out );
   cudaFree ( d_keys_in );
   cudaFree ( d_rank_by_pos );
   cudaFree ( d_flags );
   cudaFree ( d_indices_out );
   cudaFree ( d_indices_in );
   cudaFree ( d_rank_b );
   cudaFree ( d_rank_a );
   cudaFree ( d_block );

   return ok;
}
