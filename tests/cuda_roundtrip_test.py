#!/usr/bin/env python3
'''
Roundtrip tests for CUDA-enabled builds and their CPU fallback.
'''

from hashlib import md5
import os
from pathlib import Path
import random
import subprocess
import tempfile
import unittest


class CUDARoundtripTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.bzip2 = Path(os.getenv('PATH_BZIP2'))
        tmp_root = os.getenv('TMP')
        cls.path_tmp = Path(tempfile.mkdtemp(prefix='cuda-roundtrip-', dir=tmp_root))

    @classmethod
    def tearDownClass(cls):
        for path in sorted(cls.path_tmp.glob('*'), reverse=True):
            path.unlink()
        cls.path_tmp.rmdir()

    def run_bzip2(self, args, env=None, input_bytes=None):
        command = [str(self.bzip2)] + args
        proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE if input_bytes is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        out, err = proc.communicate(input_bytes)
        self.assertEqual(
            proc.returncode,
            0,
            'command failed: {}\nstderr: {}'.format(' '.join(command), err.decode('utf-8', 'replace')),
        )
        return out

    def assert_roundtrip(self, name, data, extra_env=None):
        sample = self.path_tmp / name
        compressed = self.path_tmp / (name + '.bz2')
        sample.write_bytes(data)

        env = os.environ.copy()
        if extra_env is not None:
            env.update(extra_env)

        out = self.run_bzip2(
            ['--compress', '-9', '--keep', '--stdout', str(sample)],
            env=env,
        )
        compressed.write_bytes(out)
        restored = self.run_bzip2(
            ['--decompress', '--stdout', str(compressed)],
            env=env,
        )

        self.assertEqual(md5(restored).hexdigest(), md5(data).hexdigest())
        self.assertEqual(restored, data)

    def test_large_synthetic_inputs_roundtrip_with_cuda_and_fallback(self):
        rng = random.Random(12345)
        random_bytes = bytes(rng.getrandbits(8) for _ in range(1024 * 1024))
        periodic = (b'CUDA bzip2 blocksort benchmark input. ' * 30000)[:1024 * 1024]
        repeated = b'A' * (1024 * 1024)

        for name, data in [
            ('random.bin', random_bytes),
            ('periodic.txt', periodic),
            ('repeated.bin', repeated),
        ]:
            self.assert_roundtrip(name, data)
            self.assert_roundtrip(name + '.fallback', data, {'BZ2_DISABLE_CUDA': '1'})


if __name__ == '__main__':
    unittest.main()
