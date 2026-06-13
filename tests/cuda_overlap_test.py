#!/usr/bin/env python3
'''
Source-level checks for the opt-in internal CUDA overlap pipeline.
'''

import os
from pathlib import Path
import unittest


class CUDAOverlapSurfaceTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.source = Path(os.getenv('PATH_SOURCE', '.')).resolve()

    def read_text(self, relative_path):
        return (self.source / relative_path).read_text(encoding='utf-8')

    def test_overlap_is_runtime_opt_in(self):
        bzlib = self.read_text('bzlib.c')
        self.assertIn('BZ2_CUDA_OVERLAP', bzlib)
        self.assertIn('overlapEnabled', bzlib)

    def test_overlap_uses_independent_block_slots(self):
        private_header = self.read_text('bzlib_private.h')
        self.assertIn('BZ2BlockSlot', private_header)
        self.assertIn('overlapSlots[2]', private_header)
        self.assertIn('UInt32*  arr1', private_header)
        self.assertIn('UInt32*  arr2', private_header)
        self.assertIn('UInt32*  ftab', private_header)

    def test_cuda_build_has_background_sort_worker(self):
        cmake = self.read_text('CMakeLists.txt')
        header = self.read_text('cuda/blocksort_overlap.h')
        implementation = self.read_text('cuda/blocksort_overlap.c')
        self.assertIn('Threads::Threads', cmake)
        self.assertIn('BZ2_cudaOverlapLaunch', header)
        self.assertIn('BZ2_cudaOverlapWait', header)
        self.assertIn('pthread_create', implementation)

    def test_profile_benchmark_compares_overlap_mode(self):
        benchmark = self.read_text('bench/cuda_profile_compare.py')
        self.assertIn('--compare-overlap', benchmark)
        self.assertIn('BZ2_CUDA_OVERLAP', benchmark)
        self.assertIn('profile-cuda-overlap', benchmark)

    def test_fast_mtf_is_runtime_opt_in_with_reference_fallback(self):
        private_header = self.read_text('bzlib_private.h')
        bzlib = self.read_text('bzlib.c')
        compress = self.read_text('compress.c')
        benchmark = self.read_text('bench/cuda_profile_compare.py')
        self.assertIn('fastMTFEnabled', private_header)
        self.assertIn('BZ2_FAST_MTF', bzlib)
        self.assertIn('generateMTFValuesFast', compress)
        self.assertIn('generateMTFValuesReference', compress)
        self.assertIn('--compare-fast-mtf', benchmark)

    def test_mtf_position_profile_is_runtime_opt_in(self):
        private_header = self.read_text('bzlib_private.h')
        bzlib = self.read_text('bzlib.c')
        mtf_profile = self.read_text('mtf_profile.c')
        self.assertIn('mtfProfileEnabled', private_header)
        self.assertIn('profileMTFPositions', private_header)
        self.assertIn('BZ2_MTF_PROFILE', bzlib)
        self.assertIn('record_mtf_position', mtf_profile)

    def test_cuda_can_return_bwt_last_column_for_sequential_mtf(self):
        private_header = self.read_text('bzlib_private.h')
        bzlib = self.read_text('bzlib.c')
        blocksort = self.read_text('blocksort.c')
        cuda_header = self.read_text('cuda/blocksort_cuda.h')
        cuda_impl = self.read_text('cuda/blocksort_cuda.cu')
        compress = self.read_text('compress.c')
        benchmark = self.read_text('bench/cuda_profile_compare.py')

        self.assertIn('BZ2_CUDA_BWT', bzlib)
        self.assertIn('UChar*   bwt', private_header)
        self.assertIn('blockIsBWT', private_header)
        self.assertIn('bwt_last_column_kernel', cuda_impl)
        self.assertIn('UChar* bwt', cuda_header)
        self.assertIn('s->cudaBWTEnabled', blocksort)
        self.assertIn('s->blockIsBWT', compress)
        self.assertIn('--compare-cuda-bwt', benchmark)

    def test_cuda_huffman_optimization_is_runtime_opt_in(self):
        private_header = self.read_text('bzlib_private.h')
        bzlib = self.read_text('bzlib.c')
        compress = self.read_text('compress.c')
        cuda_header = self.read_text('cuda/huffman_cuda.h')
        cuda_impl = self.read_text('cuda/huffman_cuda.cu')
        benchmark = self.read_text('bench/cuda_profile_compare.py')

        self.assertIn('BZ2_CUDA_HUFFMAN', bzlib)
        self.assertIn('cudaHuffmanEnabled', private_header)
        self.assertIn('BZ2_cudaHuffmanPrepare', cuda_header)
        self.assertIn('BZ2_cudaHuffmanIterate', cuda_header)
        self.assertIn('huffman_group_cost_kernel', cuda_impl)
        self.assertIn('s->cudaHuffmanEnabled', compress)
        self.assertIn('--compare-cuda-huffman', benchmark)

if __name__ == '__main__':
    unittest.main()
