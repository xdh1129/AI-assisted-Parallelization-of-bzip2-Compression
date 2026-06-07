#!/usr/bin/env python3
'''
Source-level checks for the optional CUDA compression path.
'''

import os
from pathlib import Path
import unittest


class CUDASurfaceTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.source = Path(os.getenv('PATH_SOURCE', '.')).resolve()

    def read_text(self, relative_path):
        return (self.source / relative_path).read_text(encoding='utf-8')

    def test_cmake_exposes_optional_cuda_build(self):
        cmake = self.read_text('CMakeLists.txt')
        self.assertIn('option(ENABLE_CUDA', cmake)
        self.assertIn('enable_language(CUDA)', cmake)
        self.assertIn('BZ2_ENABLE_CUDA', cmake)
        self.assertIn('blocksort_cuda.cu', cmake)

    def test_blocksort_has_cuda_dispatch_and_fallback(self):
        blocksort = self.read_text('blocksort.c')
        self.assertIn('cuda/blocksort_cuda.h', blocksort)
        self.assertIn('BZ2_cudaBlockSort', blocksort)
        self.assertIn('BZ2_ENABLE_CUDA', blocksort)
        self.assertIn('fallbackSort', blocksort)

    def test_cuda_wrapper_has_expected_interface_and_escape_hatch(self):
        header = self.read_text('cuda/blocksort_cuda.h')
        implementation = self.read_text('cuda/blocksort_cuda.cu')
        self.assertIn('Bool BZ2_cudaBlockSort', header)
        self.assertIn('BZ2_DISABLE_CUDA', implementation)
        self.assertIn('cub::DeviceRadixSort', implementation)
        self.assertIn('cudaMemcpy', implementation)


if __name__ == '__main__':
    unittest.main()
