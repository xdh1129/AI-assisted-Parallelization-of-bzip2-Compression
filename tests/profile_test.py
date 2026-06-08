#!/usr/bin/env python3
'''
Tests for optional internal compression profiling.
'''

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class CompressionProfileTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.bzip2 = Path(os.getenv('PATH_BZIP2')).resolve()
        cls.tmp = Path(tempfile.mkdtemp(prefix='profile-', dir=os.getenv('TMP')))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(str(cls.tmp))

    def run_bzip2(self, args, env=None):
        proc = subprocess.Popen(
            [str(self.bzip2)] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        stdout, stderr = proc.communicate()
        self.assertEqual(
            proc.returncode,
            0,
            stderr.decode('utf-8', 'replace'),
        )
        return stdout, stderr.decode('utf-8', 'replace')

    def test_profile_is_quiet_by_default_and_reports_when_enabled(self):
        sample = self.tmp / 'sample.bin'
        compressed = self.tmp / 'sample.bz2'
        data = (
            b'profile-bzip2-cuda-' * 8192 +
            bytes(range(256)) * 2048 +
            b'A' * 1024 * 128
        )
        sample.write_bytes(data)

        _, default_stderr = self.run_bzip2(
            ['--compress', '-9', '--keep', '--stdout', str(sample)],
        )
        self.assertNotIn('bzip2-profile:', default_stderr)

        env = os.environ.copy()
        env['BZ2_PROFILE'] = '1'
        profile_stdout, profile_stderr = self.run_bzip2(
            ['--compress', '-9', '--keep', '--stdout', str(sample)],
            env=env,
        )
        compressed.write_bytes(profile_stdout)

        self.assertIn('bzip2-profile: blocks=', profile_stderr)
        self.assertIn('blocksort=', profile_stderr)
        self.assertIn('mtf=', profile_stderr)
        self.assertIn('huffman_bitstream=', profile_stderr)
        self.assertIn('compress_block_total=', profile_stderr)

        restored, _ = self.run_bzip2(
            ['--decompress', '--stdout', str(compressed)],
            env=env,
        )
        self.assertEqual(restored, data)


if __name__ == '__main__':
    unittest.main()
