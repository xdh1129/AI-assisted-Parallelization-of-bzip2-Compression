#!/usr/bin/env python3
'''
Run bzip2 with BZ2_PROFILE=1 and summarize compression phase timing.
'''

from hashlib import md5
import argparse
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time


PROFILE_BLOCKS_RE = re.compile(r'^bzip2-profile:\s+blocks=(\d+)\s*$', re.MULTILINE)
PROFILE_PHASES_RE = re.compile(
    r'^bzip2-profile:\s+blocksort=([0-9.]+)s\s+'
    r'mtf=([0-9.]+)s\s+'
    r'huffman_bitstream=([0-9.]+)s\s+'
    r'compress_block_total=([0-9.]+)s\s*$',
    re.MULTILINE,
)
PROFILE_OVERLAP_RE = re.compile(
    r'^bzip2-profile:\s+pipeline_blocks=(\d+)\s+'
    r'worker_sort_wait=([0-9.]+)s\s+'
    r'overlapped_sort=([0-9.]+)s\s+'
    r'encode=([0-9.]+)s\s*$',
    re.MULTILINE,
)


def parse_profile(stderr_text):
    blocks_match = PROFILE_BLOCKS_RE.search(stderr_text)
    phases_match = PROFILE_PHASES_RE.search(stderr_text)
    if blocks_match is None or phases_match is None:
        raise RuntimeError(
            'BZ2_PROFILE output was not found. Rebuild after pulling the profiling commit.'
        )

    profile = {
        'blocks': int(blocks_match.group(1)),
        'blocksort': float(phases_match.group(1)),
        'mtf': float(phases_match.group(2)),
        'huffman_bitstream': float(phases_match.group(3)),
        'compress_block_total': float(phases_match.group(4)),
    }
    overlap_match = PROFILE_OVERLAP_RE.search(stderr_text)
    if overlap_match is not None:
        profile.update({
            'pipeline_blocks': int(overlap_match.group(1)),
            'worker_sort_wait': float(overlap_match.group(2)),
            'overlapped_sort': float(overlap_match.group(3)),
            'encode': float(overlap_match.group(4)),
        })
    return profile


def run_to_file(command, output_path, env=None):
    start = time.perf_counter()
    with output_path.open('wb') as out_file:
        proc = subprocess.Popen(
            command,
            stdout=out_file,
            stderr=subprocess.PIPE,
            env=env,
        )
        _, err = proc.communicate()
    elapsed = time.perf_counter() - start
    if proc.returncode != 0:
        raise RuntimeError(
            'command failed: {}\nstderr: {}'.format(
                ' '.join(command),
                err.decode('utf-8', 'replace'),
            )
        )
    return err.decode('utf-8', 'replace'), elapsed


def file_md5(path):
    digest = md5()
    with path.open('rb') as in_file:
        for chunk in iter(lambda: in_file.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def phase_percent(seconds, total):
    if total <= 0.0:
        return 0.0
    return (seconds / total) * 100.0


def recommend_next(profile):
    blocksort = profile['blocksort']
    mtf = profile['mtf']
    huffman = profile['huffman_bitstream']
    cpu_tail = mtf + huffman

    if cpu_tail >= blocksort:
        return (
            'cpu-gpu-overlap: CPU MTF+Huffman is now at least as large as '
            'GPU blocksort, so overlap the next blocksort with current CPU coding.'
        )
    if huffman >= mtf and huffman >= blocksort * 0.5:
        return (
            'huffman-bitstream-split: Huffman/bitstream is a large single phase; '
            'split sendMTFValues before deeper CUDA blocksort work.'
        )
    return (
        'cuda-blocksort-optimization: blocksort is still dominant, so optimize '
        'CUDA sort kernels or batch multiple blocks.'
    )


def measure(binary, input_path, block_size, disable_cuda, overlap, fast_mtf, tmp_dir):
    env = os.environ.copy()
    env['BZ2_PROFILE'] = '1'
    if disable_cuda:
        mode = 'profile-cpu-fallback'
    elif overlap and fast_mtf:
        mode = 'profile-cuda-overlap-fast-mtf'
    elif overlap:
        mode = 'profile-cuda-overlap'
    elif fast_mtf:
        mode = 'profile-cuda-fast-mtf'
    else:
        mode = 'profile-cuda-enabled'
    if disable_cuda:
        env['BZ2_DISABLE_CUDA'] = '1'
    else:
        env.pop('BZ2_DISABLE_CUDA', None)
    if overlap:
        env['BZ2_CUDA_OVERLAP'] = '1'
    else:
        env.pop('BZ2_CUDA_OVERLAP', None)
    if fast_mtf:
        env['BZ2_FAST_MTF'] = '1'
    else:
        env.pop('BZ2_FAST_MTF', None)

    compressed_path = tmp_dir / (input_path.name + '.' + mode + '.bz2')
    restored_path = tmp_dir / (input_path.name + '.' + mode + '.restored')

    stderr_text, compress_seconds = run_to_file(
        [str(binary), '--compress', block_size, '--keep', '--stdout', str(input_path)],
        compressed_path,
        env=env,
    )
    profile = parse_profile(stderr_text)

    _, decompress_seconds = run_to_file(
        [str(binary), '--decompress', '--stdout', str(compressed_path)],
        restored_path,
        env=env,
    )

    if file_md5(restored_path) != file_md5(input_path):
        raise RuntimeError('{} decompressed bytes do not match input'.format(mode))

    return {
        'mode': mode,
        'compress_seconds': compress_seconds,
        'decompress_seconds': decompress_seconds,
        'compressed_bytes': compressed_path.stat().st_size,
        'input_bytes': input_path.stat().st_size,
        'profile': profile,
    }


def print_result(result):
    profile = result['profile']
    total = profile['compress_block_total']
    cpu_tail = profile['mtf'] + profile['huffman_bitstream']
    other = max(0.0, total - profile['blocksort'] - cpu_tail)
    ratio = float(result['compressed_bytes']) / float(result['input_bytes'])

    print(
        '{mode}: compress={compress_seconds:.6f}s decompress={decompress_seconds:.6f}s '
        'compressed={compressed_bytes} ratio={ratio:.6f}'.format(
            ratio=ratio,
            **result
        )
    )
    print(
        'phase-detail: blocks={blocks} total={total:.6f}s '
        'blocksort={blocksort:.6f}s ({blocksort_pct:.2f}%) '
        'mtf={mtf:.6f}s ({mtf_pct:.2f}%) '
        'huffman_bitstream={huffman:.6f}s ({huffman_pct:.2f}%) '
        'cpu_tail={cpu_tail:.6f}s ({cpu_tail_pct:.2f}%) '
        'other={other:.6f}s ({other_pct:.2f}%)'.format(
            blocks=profile['blocks'],
            total=total,
            blocksort=profile['blocksort'],
            blocksort_pct=phase_percent(profile['blocksort'], total),
            mtf=profile['mtf'],
            mtf_pct=phase_percent(profile['mtf'], total),
            huffman=profile['huffman_bitstream'],
            huffman_pct=phase_percent(profile['huffman_bitstream'], total),
            cpu_tail=cpu_tail,
            cpu_tail_pct=phase_percent(cpu_tail, total),
            other=other,
            other_pct=phase_percent(other, total),
        )
    )
    print('next-step: {}'.format(recommend_next(profile)))
    if 'pipeline_blocks' in profile:
        print(
            'overlap-detail: pipeline_blocks={pipeline_blocks} '
            'worker_sort_wait={worker_sort_wait:.6f}s '
            'overlapped_sort={overlapped_sort:.6f}s '
            'encode={encode:.6f}s'.format(**profile)
        )


def main():
    parser = argparse.ArgumentParser(description='Profile bzip2 compression phases with BZ2_PROFILE=1.')
    parser.add_argument('--bzip2', required=True, type=Path, help='Path to the bzip2 binary.')
    parser.add_argument('--input', required=True, type=Path, help='Input file to compress.')
    parser.add_argument('--block-size', default='-9', choices=['-1', '-2', '-3', '-4', '-5', '-6', '-7', '-8', '-9'])
    parser.add_argument('--disable-cuda', action='store_true', help='Set BZ2_DISABLE_CUDA=1 and run only CPU fallback.')
    parser.add_argument('--compare-cpu', action='store_true', help='Also run CPU fallback after CUDA-enabled profiling.')
    parser.add_argument('--compare-overlap', action='store_true', help='Also run with BZ2_CUDA_OVERLAP=1.')
    parser.add_argument('--compare-fast-mtf', action='store_true', help='Also run with BZ2_FAST_MTF=1.')
    parser.add_argument('--tmp-dir', type=Path, default=None, help='Directory for temporary compressed/restored files.')
    args = parser.parse_args()

    modes = [(False, False, False)]
    if args.compare_overlap:
        modes.append((False, True, False))
    if args.compare_fast_mtf:
        modes.append((False, False, True))
    if args.compare_overlap and args.compare_fast_mtf:
        modes.append((False, True, True))
    if args.compare_cpu:
        modes.append((True, False, False))
    if args.disable_cuda:
        modes = [(True, False, False)]

    with tempfile.TemporaryDirectory(dir=str(args.tmp_dir) if args.tmp_dir else None) as tmp:
        tmp_dir = Path(tmp)
        for disable_cuda, overlap, fast_mtf in modes:
            print_result(measure(
                args.bzip2, args.input, args.block_size,
                disable_cuda, overlap, fast_mtf, tmp_dir,
            ))


if __name__ == '__main__':
    main()
