#!/usr/bin/env python3
"""Construct (and optionally run) profiling commands. Linux: perf, valgrind."""
import subprocess


def _pbzx_args(pbzx, infile, outfile, threads, block_size, level):
    return [pbzx, "-i", infile, "-o", outfile,
            "--threads", str(threads), "--block-size", str(block_size),
            "--level", str(level)]


def perf_stat_cmd(pbzx, infile, outfile, threads, block_size, level):
    return ["perf", "stat", "-d",
            *_pbzx_args(pbzx, infile, outfile, threads, block_size, level)]


def perf_record_cmd(pbzx, infile, outfile, threads, block_size, level,
                    data="perf.data"):
    return ["perf", "record", "-o", data,
            *_pbzx_args(pbzx, infile, outfile, threads, block_size, level)]


def massif_cmd(pbzx, infile, outfile, threads, block_size, level,
               out="massif.out"):
    return ["valgrind", "--tool=massif", f"--massif-out-file={out}",
            *_pbzx_args(pbzx, infile, outfile, threads, block_size, level)]


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)
