import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bench"))
import plot  # noqa: E402


def test_derive_metrics():
    rows = [
        {"input": "a", "block_size": "900000", "threads": "1", "compress_seconds": "2.0"},
        {"input": "a", "block_size": "900000", "threads": "2", "compress_seconds": "1.0"},
        {"input": "a", "block_size": "900000", "threads": "4", "compress_seconds": "0.5"},
    ]
    out = plot.derive_metrics(rows)
    by_t = {int(r["threads"]): r for r in out}
    assert abs(by_t[1]["speedup"] - 1.0) < 1e-9
    assert abs(by_t[2]["speedup"] - 2.0) < 1e-9
    assert abs(by_t[4]["parallel_efficiency"] - 1.0) < 1e-9


def test_plot_speedup_writes_png(tmp_path):
    rows = plot.derive_metrics([
        {"input": "a", "block_size": "900000", "threads": "1", "compress_seconds": "2.0"},
        {"input": "a", "block_size": "900000", "threads": "2", "compress_seconds": "1.0"},
    ])
    out = tmp_path / "s.png"
    plot.plot_speedup(rows, str(out))
    assert out.exists() and out.stat().st_size > 0
