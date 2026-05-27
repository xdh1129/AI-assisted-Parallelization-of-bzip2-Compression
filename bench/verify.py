#!/usr/bin/env python3
"""Round-trip correctness oracle: pbzx compress -> bunzip2 decompress -> cmp."""
import filecmp
import os
import subprocess
import sys


def roundtrip_ok(pbzx, infile, workdir):
    """Compress infile with pbzx, decompress with bunzip2, compare to original."""
    bz = os.path.join(workdir, "out.bz2")
    dec = os.path.join(workdir, "out.dec")
    subprocess.run([pbzx, "-i", infile, "-o", bz], check=True,
                   stdout=subprocess.DEVNULL)
    with open(dec, "wb") as f:
        subprocess.run(["bunzip2", "-c", bz], check=True, stdout=f)
    return filecmp.cmp(infile, dec, shallow=False)


def main(argv):
    if len(argv) < 3:
        print("usage: verify.py <pbzx> <file>...", file=sys.stderr)
        return 2
    pbzx, files = argv[1], argv[2:]
    import tempfile
    ok = True
    with tempfile.TemporaryDirectory() as d:
        for fp in files:
            r = roundtrip_ok(pbzx, fp, d)
            print(f"{'PASS' if r else 'FAIL'}  {fp}")
            ok = ok and r
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
