#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from handoff_lib import extract_override_block_text, load_agents_overrides


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract Agent Handoff Overrides from AGENTS.md.")
    parser.add_argument("--repo-root", default=".", help="目标仓库根目录，默认当前目录")
    parser.add_argument("--pretty", action="store_true", help="格式化 JSON 输出")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    block = extract_override_block_text(repo_root / "AGENTS.md")
    values, ignored = load_agents_overrides(repo_root)
    payload = {
        "found": bool(block),
        "values": values,
        "ignored_keys": ignored,
    }
    if args.pretty:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
