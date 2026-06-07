#!/usr/bin/env python3
'''
Compare bzip2 compression with CUDA enabled and with CUDA disabled.
'''

from hashlib import md5
import argparse
import os
from pathlib import Path
import subprocess
import tempfile
import time


def run_command(command, env=None):
    start = time.perf_counter()
    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    out, err = proc.communicate()
    elapsed = time.perf_counter() - start
    if proc.returncode != 0:
        raise RuntimeError(
            'command failed: {}\nstderr: {}'.format(
                ' '.join(command),
                err.decode('utf-8', 'replace'),
            )
        )
    return out, elapsed


def measure(binary, input_path, block_size, disable_cuda):
    env = os.environ.copy()
    mode = 'cpu-fallback' if disable_cuda else 'cuda-enabled'
    if disable_cuda:
        env['BZ2_DISABLE_CUDA'] = '1'
    else:
        env.pop('BZ2_DISABLE_CUDA', None)

    compressed, compress_seconds = run_command(
        [str(binary), '--compress', block_size, '--keep', '--stdout', str(input_path)],
        env=env,
    )

    with tempfile.NamedTemporaryFile(suffix='.bz2', delete=False) as tmp:
        tmp.write(compressed)
        compressed_path = Path(tmp.name)

    try:
        restored, decompress_seconds = run_command(
            [str(binary), '--decompress', '--stdout', str(compressed_path)],
            env=env,
        )
    finally:
        compressed_path.unlink()

    original = input_path.read_bytes()
    if md5(restored).hexdigest() != md5(original).hexdigest():
        raise RuntimeError('{} decompressed bytes do not match input'.format(mode))

    return {
        'mode': mode,
        'compress_seconds': compress_seconds,
        'decompress_seconds': decompress_seconds,
        'compressed_bytes': len(compressed),
        'input_bytes': len(original),
    }


def main():
    parser = argparse.ArgumentParser(description='Compare CUDA bzip2 compression against CPU fallback.')
    parser.add_argument('--bzip2', required=True, type=Path, help='Path to a CUDA-enabled bzip2 binary.')
    parser.add_argument('--input', required=True, type=Path, help='Input file to compress.')
    parser.add_argument('--block-size', default='-9', choices=['-1', '-2', '-3', '-4', '-5', '-6', '-7', '-8', '-9'])
    args = parser.parse_args()

    for result in [
        measure(args.bzip2, args.input, args.block_size, False),
        measure(args.bzip2, args.input, args.block_size, True),
    ]:
        ratio = float(result['compressed_bytes']) / float(result['input_bytes'])
        print(
            '{mode}: compress={compress_seconds:.6f}s decompress={decompress_seconds:.6f}s '
            'compressed={compressed_bytes} ratio={ratio:.6f}'.format(
                ratio=ratio,
                **result
            )
        )


if __name__ == '__main__':
    main()
