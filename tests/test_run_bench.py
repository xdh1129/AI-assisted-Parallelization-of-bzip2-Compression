import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bench"))
import run_bench  # noqa: E402


def test_parse_stats():
    line = ("PBZX_STATS input_bytes=1000 output_bytes=200 block_size=900000 "
            "threads=4 level=9 blocks=2 compress_seconds=0.123456\n")
    s = run_bench.parse_stats("noise\n" + line + "tail\n")
    assert s["input_bytes"] == 1000
    assert s["output_bytes"] == 200
    assert s["threads"] == 4
    assert s["compress_seconds"] == 0.123456


def test_parse_time_v():
    err = (
        "\tCommand being timed: \"pbzx\"\n"
        "\tMaximum resident set size (kbytes): 20480\n"
        "\tElapsed (wall clock) time (h:mm:ss or m:ss): 0:01.50\n"
    )
    tv = run_bench.parse_time_v(err)
    assert tv["max_rss_kb"] == 20480
    assert abs(tv["elapsed_s"] - 1.5) < 1e-6
