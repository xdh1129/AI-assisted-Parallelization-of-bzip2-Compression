import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PBZX = ROOT / "pbzx"
sys.path.insert(0, str(ROOT / "bench"))
import verify  # noqa: E402


@pytest.fixture(scope="module")
def pbzx_bin():
    if not PBZX.exists():
        subprocess.run(["make"], cwd=ROOT, check=True)
    return str(PBZX)


@pytest.mark.parametrize("size", [0, 1, 100, 900000, 900001, 5_000_000])
def test_roundtrip_sizes(pbzx_bin, tmp_path, size):
    f = tmp_path / f"in_{size}.bin"
    f.write_bytes(os.urandom(size))
    assert verify.roundtrip_ok(pbzx_bin, str(f), str(tmp_path))


def test_roundtrip_compressible(pbzx_bin, tmp_path):
    f = tmp_path / "text.txt"
    f.write_bytes(b"the quick brown fox " * 200000)
    assert verify.roundtrip_ok(pbzx_bin, str(f), str(tmp_path))
