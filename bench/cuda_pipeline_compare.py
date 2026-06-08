#!/usr/bin/env python3
'''
Compare single-stream bzip2 compression with a multi-stream chunk pipeline.
'''

from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import md5
from pathlib import Path
import argparse
import math
import os
import shutil
import subprocess
import tempfile
import time


def file_md5(path):
    digest = md5()
    with path.open('rb') as handle:
        while True:
            data = handle.read(1024 * 1024)
            if data == b'':
                break
            digest.update(data)
    return digest.hexdigest()


def stdout_md5(command, env=None):
    digest = md5()
    start = time.perf_counter()
    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    while True:
        data = proc.stdout.read(1024 * 1024)
        if data == b'':
            break
        digest.update(data)
    _, err = proc.communicate()
    elapsed = time.perf_counter() - start
    if proc.returncode != 0:
        raise RuntimeError(
            'command failed: {}\nstderr: {}'.format(
                ' '.join(command),
                err.decode('utf-8', 'replace'),
            )
        )
    return digest.hexdigest(), elapsed


def stdout_to_file(command, output_path, env=None):
    start = time.perf_counter()
    with output_path.open('wb') as output:
        proc = subprocess.Popen(
            command,
            stdout=output,
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
    return elapsed


def compress_chunk(task):
    (
        index,
        input_path,
        offset,
        length,
        bzip2,
        block_size,
        output_path,
        env_items,
    ) = task
    env = os.environ.copy()
    env.update(dict(env_items))

    with open(input_path, 'rb') as input_file:
        input_file.seek(offset)
        chunk = input_file.read(length)

    start = time.perf_counter()
    with open(output_path, 'wb') as output_file:
        proc = subprocess.Popen(
            [bzip2, '--compress', block_size, '--stdout'],
            stdin=subprocess.PIPE,
            stdout=output_file,
            stderr=subprocess.PIPE,
            env=env,
        )
        _, err = proc.communicate(chunk)
    elapsed = time.perf_counter() - start
    if proc.returncode != 0:
        raise RuntimeError(
            'chunk {} failed: {}'.format(
                index,
                err.decode('utf-8', 'replace'),
            )
        )

    return index, elapsed, os.path.getsize(output_path)


def build_chunks(input_size, chunk_bytes):
    chunks = []
    count = int(math.ceil(float(input_size) / float(chunk_bytes)))
    for index in range(count):
        offset = index * chunk_bytes
        length = min(chunk_bytes, input_size - offset)
        chunks.append((index, offset, length))
    return chunks


def validate_roundtrip(binary, compressed_path, expected_md5, env):
    restored_md5, decompress_seconds = stdout_md5(
        [str(binary), '--decompress', '--stdout', str(compressed_path)],
        env=env,
    )
    if restored_md5 != expected_md5:
        raise RuntimeError(
            '{} decompressed bytes do not match input hash {}'.format(
                compressed_path,
                expected_md5,
            )
        )
    return decompress_seconds


def measure_sequential(binary, input_path, block_size, expected_md5, env, temp_dir):
    output_path = temp_dir / 'sequential.bz2'
    compress_seconds = stdout_to_file(
        [str(binary), '--compress', block_size, '--keep', '--stdout', str(input_path)],
        output_path,
        env=env,
    )
    decompress_seconds = validate_roundtrip(binary, output_path, expected_md5, env)
    return {
        'mode': 'sequential-cuda-enabled',
        'compress_seconds': compress_seconds,
        'decompress_seconds': decompress_seconds,
        'compressed_bytes': output_path.stat().st_size,
    }


def measure_pipeline(binary, input_path, block_size, expected_md5, env, temp_dir, chunk_mb, workers):
    input_size = input_path.stat().st_size
    chunk_bytes = chunk_mb * 1024 * 1024
    chunks = build_chunks(input_size, chunk_bytes)
    chunk_dir = temp_dir / 'chunks'
    chunk_dir.mkdir()
    output_path = temp_dir / 'pipeline.bz2'
    env_items = tuple((key, value) for key, value in env.items())
    tasks = [
        (
            index,
            str(input_path),
            offset,
            length,
            str(binary),
            block_size,
            str(chunk_dir / ('chunk_{:06d}.bz2'.format(index))),
            env_items,
        )
        for index, offset, length in chunks
    ]

    chunk_results = {}
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(compress_chunk, task) for task in tasks]
        for future in as_completed(futures):
            index, elapsed, compressed_bytes = future.result()
            chunk_results[index] = (elapsed, compressed_bytes)

    with output_path.open('wb') as output:
        for index, _, _ in chunks:
            with (chunk_dir / ('chunk_{:06d}.bz2'.format(index))).open('rb') as chunk_file:
                shutil.copyfileobj(chunk_file, output)
    compress_seconds = time.perf_counter() - start
    decompress_seconds = validate_roundtrip(binary, output_path, expected_md5, env)

    return {
        'mode': 'pipeline-cuda-enabled',
        'compress_seconds': compress_seconds,
        'decompress_seconds': decompress_seconds,
        'compressed_bytes': output_path.stat().st_size,
        'chunks': len(chunks),
        'workers': workers,
        'chunk_mib': chunk_mb,
        'slowest_chunk_seconds': max((item[0] for item in chunk_results.values()), default=0.0),
    }, output_path


def print_result(result, input_bytes):
    ratio = float(result['compressed_bytes']) / float(input_bytes)
    print(
        '{mode}: compress={compress_seconds:.6f}s decompress={decompress_seconds:.6f}s '
        'compressed={compressed_bytes} ratio={ratio:.6f}'.format(
            ratio=ratio,
            **result
        )
    )
    if result['mode'].startswith('pipeline'):
        print(
            'pipeline-detail: chunks={chunks} workers={workers} chunk_mib={chunk_mib} '
            'slowest_chunk={slowest_chunk_seconds:.6f}s'.format(**result)
        )


def main():
    parser = argparse.ArgumentParser(
        description='Compare CUDA bzip2 single-stream compression with chunked pipeline compression.'
    )
    parser.add_argument('--bzip2', required=True, type=Path, help='Path to a CUDA-enabled bzip2 binary.')
    parser.add_argument('--input', required=True, type=Path, help='Input file to compress.')
    parser.add_argument('--block-size', default='-9', choices=['-1', '-2', '-3', '-4', '-5', '-6', '-7', '-8', '-9'])
    parser.add_argument('--chunk-mb', default=64, type=int, help='Chunk size for the pipeline in MiB.')
    parser.add_argument('--workers', default=4, type=int, help='Number of parallel compression workers.')
    parser.add_argument('--output', type=Path, help='Optional path for the concatenated pipeline .bz2 output.')
    parser.add_argument('--disable-cuda', action='store_true', help='Set BZ2_DISABLE_CUDA=1 for both measurements.')
    args = parser.parse_args()

    binary = args.bzip2.expanduser().resolve()
    input_path = args.input.expanduser().resolve()
    if args.chunk_mb <= 0:
        raise SystemExit('--chunk-mb must be positive')
    if args.workers <= 0:
        raise SystemExit('--workers must be positive')
    if not binary.exists():
        raise SystemExit('{} does not exist'.format(binary))
    if not input_path.exists():
        raise SystemExit('{} does not exist'.format(input_path))

    env = os.environ.copy()
    if args.disable_cuda:
        env['BZ2_DISABLE_CUDA'] = '1'
    else:
        env.pop('BZ2_DISABLE_CUDA', None)

    input_bytes = input_path.stat().st_size
    expected_md5 = file_md5(input_path)
    with tempfile.TemporaryDirectory(prefix='bzip2-pipeline-') as temp_name:
        temp_dir = Path(temp_name)
        sequential = measure_sequential(
            binary,
            input_path,
            args.block_size,
            expected_md5,
            env,
            temp_dir,
        )
        pipeline, pipeline_output = measure_pipeline(
            binary,
            input_path,
            args.block_size,
            expected_md5,
            env,
            temp_dir,
            args.chunk_mb,
            args.workers,
        )

        print_result(sequential, input_bytes)
        print_result(pipeline, input_bytes)
        print(
            'pipeline-speedup: {:.6f}x'.format(
                sequential['compress_seconds'] / pipeline['compress_seconds']
            )
        )

        if args.output is not None:
            output_path = args.output.expanduser().resolve()
            shutil.copyfile(str(pipeline_output), str(output_path))
            print('pipeline-output: {}'.format(output_path))


if __name__ == '__main__':
    main()
