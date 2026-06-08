#!/usr/bin/env python3
'''
Tests for the multi-stream CUDA pipeline benchmark helper.
'''

from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


class CUDAPipelineTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.source = Path(os.getenv('PATH_SOURCE', '.')).resolve()
        cls.bzip2 = Path(os.getenv('PATH_BZIP2')).resolve()
        cls.tmp = Path(tempfile.mkdtemp(prefix='cuda-pipeline-', dir=os.getenv('TMP')))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(str(cls.tmp))

    def test_pipeline_output_roundtrips_concatenated_chunks(self):
        script = self.source / 'bench' / 'cuda_pipeline_compare.py'
        sample = self.tmp / 'sample.bin'
        output = self.tmp / 'sample.pipeline.bz2'
        data = (
            (b'pipeline-bzip2-cuda-' * 4096) +
            bytes(range(256)) * 4096 +
            (b'\0' * 1024 * 1024)
        )
        sample.write_bytes(data)

        env = os.environ.copy()
        env['BZ2_DISABLE_CUDA'] = '1'
        proc = subprocess.Popen(
            [
                sys.executable,
                str(script),
                '--bzip2',
                str(self.bzip2),
                '--input',
                str(sample),
                '--chunk-mb',
                '1',
                '--workers',
                '2',
                '--block-size',
                '-1',
                '--output',
                str(output),
            ],
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
        self.assertIn('pipeline-cuda-enabled:', stdout.decode('utf-8', 'replace'))
        self.assertIn('pipeline-speedup:', stdout.decode('utf-8', 'replace'))
        self.assertTrue(output.exists())

        restored = subprocess.check_output(
            [str(self.bzip2), '--decompress', '--stdout', str(output)],
            env=env,
        )
        self.assertEqual(restored, data)


if __name__ == '__main__':
    unittest.main()
