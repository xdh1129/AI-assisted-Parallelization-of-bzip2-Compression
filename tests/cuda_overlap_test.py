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


if __name__ == '__main__':
    unittest.main()
