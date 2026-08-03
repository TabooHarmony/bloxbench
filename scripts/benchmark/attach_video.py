#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.benchmark.review_runner import attach_videos


def main() -> int:
    parser = argparse.ArgumentParser(description="Attach verified viewport-only video to a preserved review run")
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--video", action="append", required=True, type=Path)
    parser.add_argument("--video-proof", action="append", required=True, type=Path)
    args = parser.parse_args()
    result = attach_videos(args.run_dir, tuple(args.video), tuple(args.video_proof))
    print(json.dumps({"run_dir": str(result.run_dir), "state": result.state, "evidence_state": result.evidence_state}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
