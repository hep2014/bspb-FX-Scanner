"""Verify the input snapshot and reproduce the published research."""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def verify_inputs():
    for line in (DATA / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        expected, name = line.split("  ", 1)
        path = DATA / name
        with path.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != expected:
            raise ValueError(f"Input differs from the published data: {name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cuad", type=Path, help="Separately downloaded CUAD_v1.zip")
    args = parser.parse_args()
    verify_inputs()
    for name in ("run_hedgelab.py", "run_investment.py", "audit_investment.py", "run_macro.py", "run_scanner.py"):
        command = [sys.executable, str(ROOT / "scripts" / name)]
        if name == "run_scanner.py" and args.cuad:
            command.extend(("--cuad", str(args.cuad.resolve(strict=True))))
        subprocess.run(command, cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
