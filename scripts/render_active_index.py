#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from handoff_lib import ensure_handoff_root, json_dump, write_index_and_active


def main() -> int:
    parser = argparse.ArgumentParser(description="Render .agent-handoff/ACTIVE.md and index.json from task manifests.")
    parser.add_argument("--repo-root", default=".", help="目标仓库根目录，默认当前目录")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    ensure_handoff_root(repo_root)
    index_data = write_index_and_active(repo_root)
    print(json_dump(index_data), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
