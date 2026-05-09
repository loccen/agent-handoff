#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from handoff_lib import (
    ALLOWED_ROOT_ENTRIES,
    HANDOFF_ROOT,
    REQUIRED_TASK_ENTRIES,
    collect_manifests,
    ensure_handoff_root,
    load_agents_overrides,
    read_text,
    relative_to_repo,
    validate_manifest_fields,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate .agent-handoff structure and manifests.")
    parser.add_argument("--repo-root", default=".", help="目标仓库根目录，默认当前目录")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    root = ensure_handoff_root(repo_root)
    errors: list[str] = []
    warnings: list[str] = []

    root_entries = {path.name for path in root.iterdir()}
    extras = sorted(root_entries - ALLOWED_ROOT_ENTRIES)
    if extras:
        errors.append(f"{HANDOFF_ROOT} 根目录存在未允许条目：{', '.join(extras)}")

    for bucket in ("tasks", "archive"):
        bucket_root = root / bucket
        for task_dir in sorted(path for path in bucket_root.iterdir() if path.is_dir()):
            entries = {path.name for path in task_dir.iterdir()}
            missing = sorted(REQUIRED_TASK_ENTRIES - entries)
            if missing:
                errors.append(f"{relative_to_repo(repo_root, task_dir)} 缺少条目：{', '.join(missing)}")
                continue
            manifest_path = task_dir / "manifest.json"
            try:
                manifest = json.loads(read_text(manifest_path))
            except json.JSONDecodeError as exc:
                errors.append(f"{relative_to_repo(repo_root, manifest_path)} JSON 非法：{exc}")
                continue
            for error in validate_manifest_fields(manifest):
                errors.append(f"{relative_to_repo(repo_root, manifest_path)} {error}")
            if bucket == "archive" and manifest.get("status") != "archived":
                errors.append(f"{relative_to_repo(repo_root, manifest_path)} 位于 archive 但 status 不是 archived")
            if bucket == "tasks" and manifest.get("status") == "archived":
                warnings.append(f"{relative_to_repo(repo_root, manifest_path)} 已 archived，但目录尚未迁入 archive/")

            task_text = read_text(task_dir / "task.md")
            handoff_text = read_text(task_dir / "handoff.md")
            if len(handoff_text) >= len(task_text):
                warnings.append(f"{relative_to_repo(repo_root, task_dir / 'handoff.md')} 未明显短于 task.md")

    overrides, ignored = load_agents_overrides(repo_root)
    if ignored:
        warnings.append(f"AGENTS.md overrides 存在未知 key，已忽略：{', '.join(ignored)}")
    if not isinstance(overrides, dict):
        errors.append("AGENTS.md overrides 解析失败")

    active, archived = collect_manifests(repo_root)
    if not active and not archived:
        warnings.append("当前没有任何 manifest；如果这是新仓库，请先运行 bootstrap_handoff.py")

    if errors:
        print("VALIDATION_STATUS=failed")
        for error in errors:
            print(f"ERROR: {error}")
        for warning in warnings:
            print(f"WARNING: {warning}")
        return 1

    print("VALIDATION_STATUS=passed")
    for warning in warnings:
        print(f"WARNING: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
