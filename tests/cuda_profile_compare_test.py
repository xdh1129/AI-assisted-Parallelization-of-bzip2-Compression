#!/usr/bin/env python3
'''
Tests for the CUDA profile comparison benchmark helper.
'''

import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


class CUDAProfileCompareTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.source = Path(os.getenv('PATH_SOURCE', '.')).resolve()
        cls.bzip2 = Path(os.getenv('PATH_BZIP2')).resolve()
        cls.tmp = Path(tempfile.mkdtemp(prefix='cuda-profile-', dir=os.getenv('TMP')))
        script = cls.source / 'bench' / 'cuda_profile_compare.py'
        spec = importlib.util.spec_from_file_location('cuda_profile_compare', script)
        cls.profile_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.profile_module)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(str(cls.tmp))

    def test_parse_profile_stderr(self):
        stderr = (
            'bzip2-profile: blocks=3\n'
            'bzip2-profile: blocksort=1.250000s mtf=0.500000s '
            'huffman_bitstream=0.750000s compress_block_total=2.700000s\n'
            'bzip2-profile: pipeline_blocks=2 worker_sort_wait=0.100000s '
            'overlapped_sort=1.200000s encode=1.100000s\n'
        )

        profile = self.profile_module.parse_profile(stderr)

        self.assertEqual(profile['blocks'], 3)
        self.assertAlmostEqual(profile['blocksort'], 1.25)
        self.assertAlmostEqual(profile['mtf'], 0.5)
        self.assertAlmostEqual(profile['huffman_bitstream'], 0.75)
        self.assertAlmostEqual(profile['compress_block_total'], 2.7)
        self.assertEqual(profile['pipeline_blocks'], 2)
        self.assertAlmostEqual(profile['worker_sort_wait'], 0.1)

    def test_profile_helper_reports_phase_percentages(self):
        script = self.source / 'bench' / 'cuda_profile_compare.py'
        sample = self.tmp / 'sample.bin'
        data = (
            b'profile-compare-bzip2-' * 4096 +
            bytes(range(256)) * 1024 +
            b'Z' * 1024 * 64
        )
        sample.write_bytes(data)

        proc = subprocess.Popen(
            [
                sys.executable,
                str(script),
                '--bzip2',
                str(self.bzip2),
                '--input',
                str(sample),
                '--block-size',
                '-1',
                '--disable-cuda',
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = proc.communicate()

        self.assertEqual(proc.returncode, 0, stderr.decode('utf-8', 'replace'))
        text = stdout.decode('utf-8', 'replace')
        self.assertIn('profile-cpu-fallback:', text)
        self.assertIn('blocksort=', text)
        self.assertIn('mtf=', text)
        self.assertIn('huffman_bitstream=', text)
        self.assertIn('next-step:', text)


if __name__ == '__main__':
    unittest.main()
