import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bench"))
import profilers  # noqa: E402


def test_perf_stat_cmd():
    c = profilers.perf_stat_cmd("./pbzx", "in", "out.bz2", 8, 900000, 9)
    assert c[:3] == ["perf", "stat", "-d"]
    assert c[c.index("--threads") + 1] == "8"
    assert "./pbzx" in c


def test_massif_cmd():
    c = profilers.massif_cmd("./pbzx", "in", "out.bz2", 4, 1000, 5, out="m.out")
    assert c[0] == "valgrind"
    assert "--tool=massif" in c
    assert "--massif-out-file=m.out" in c
