#!/usr/bin/env python3
"""
Frontend Bundle Size Benchmark — gzipped total.
Runs pnpm build, measures total gzip-compressed bytes of JS+CSS in dist/assets.
Deterministic, environment-independent.

Usage: python scripts/benchmark_frontend.py
Output: {"primary": <total_gzip_bytes>}
Exit: 0 on success, non-zero on error
"""
import gzip
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DIST_DIR = PROJECT_ROOT / "dist" / "assets"


def log(msg: str) -> None:
    print(f"[benchmark] {msg}", flush=True)


def get_gzip_size() -> int:
    """Return total gzip-compressed bytes of all .js and .css files in dist/assets."""
    total = 0
    if DIST_DIR.exists():
        for f in DIST_DIR.iterdir():
            if f.suffix in (".js", ".css"):
                with open(f, "rb") as fh:
                    total += len(gzip.compress(fh.read()))
    return total


def run_build() -> bool:
    """Run pnpm build. Returns True on success."""
    log("Running pnpm build...")

    dist = PROJECT_ROOT / "dist"
    if dist.exists():
        shutil.rmtree(dist)

    env = os.environ.copy()
    result = subprocess.run(
        ["pnpm", "run", "build"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
        env=env,
    )
    if result.returncode != 0:
        log(f"BUILD FAILED:\n{result.stderr[-1000:]}")
        return False
    return True


def main() -> int:
    log("=" * 60)
    log("Frontend Bundle Size Benchmark — Gzip (3-run average)")
    log("=" * 60)

    scores = []
    for i in range(3):
        print(f"  Run {i+1}/3...", end=" ", flush=True)
        if not run_build():
            return 1
        size = get_gzip_size()
        scores.append(size)
        print(f"{size:,} gzip bytes")

    mean = sum(scores) / len(scores)
    variance = (max(scores) - min(scores)) / mean * 100 if mean > 0 else 0

    log(f"Mean: {mean:,.0f} gzip bytes")
    log(f"Variance: {variance:.2f}%")

    if variance > 5:
        log("WARNING: High variance. Results may be unstable.")

    result = {"primary": round(mean, 2)}
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
