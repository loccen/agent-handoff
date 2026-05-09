#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from handoff_lib import (
    PROTOCOL_VERSION,
    SKILL_REVISION,
    detect_ai_task_path,
    detect_branch,
    detect_default_owner,
    ensure_handoff_root,
    generate_task_id,
    json_dump,
    load_agents_overrides,
    now_iso,
    render_template,
    sync_ai_task,
    write_index_and_active,
    write_text,
)


def bullet_block(items: list[str], fallback: str) -> str:
    if not items:
        return f"- {fallback}"
    return "\n".join(f"- {item}" for item in items)


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap .agent-handoff and a new task bundle.")
    parser.add_argument("--repo-root", default=".", help="目标仓库根目录，默认当前目录")
    parser.add_argument("--title", required=True, help="任务标题")
    parser.add_argument("--task-id", help="手动指定 task-id，默认自动生成")
    parser.add_argument("--owner", action="append", default=[], help="可重复，指定 owners")
    parser.add_argument("--truth-source", action="append", default=[], help="可重复，指定事实源")
    parser.add_argument("--required-check", action="append", default=[], help="可重复，指定验收检查")
    parser.add_argument("--next-step", default="补充任务事实与首个可执行动作", help="下一步")
    parser.add_argument("--status", default="active", help="初始状态，默认 active")
    parser.add_argument("--force", action="store_true", help="若任务目录已存在则覆盖")
    parser.add_argument("--no-ai-task-sync", action="store_true", help="禁用 ai-task 镜像同步")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    root = ensure_handoff_root(repo_root)
    overrides, _ignored = load_agents_overrides(repo_root)

    created_at = now_iso()
    updated_at = created_at
    task_id = args.task_id or generate_task_id(args.title)
    task_dir = root / "tasks" / task_id
    if task_dir.exists() and not args.force:
        raise SystemExit(f"任务目录已存在：{task_dir}")
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "evidence").mkdir(exist_ok=True)

    owners = args.owner or detect_default_owner(repo_root)
    truth_sources = args.truth_source or list(overrides.get("truth_sources", []))
    required_checks = args.required_check or list(overrides.get("required_checks", []))
    branch = detect_branch(repo_root)
    integrations = {}
    ai_task_path = detect_ai_task_path(repo_root)
    if ai_task_path:
        integrations["codex"] = {"ai_task_path": ai_task_path}

    template_root = Path(__file__).resolve().parent.parent / "templates"
    mapping = {
        "TASK_ID": task_id,
        "TITLE": args.title,
        "CREATED_AT": created_at,
        "UPDATED_AT": updated_at,
        "STATUS": args.status,
        "BRANCH": branch,
        "WORKTREE": str(repo_root),
        "NEXT_STEP": args.next_step,
        "OWNERS": json.dumps(owners, ensure_ascii=False),
        "TRUTH_SOURCES": bullet_block(truth_sources, "待补充"),
        "TRUTH_SOURCES_JSON": json.dumps(truth_sources, ensure_ascii=False),
        "REQUIRED_CHECKS": bullet_block(required_checks, "待补充"),
        "PROTOCOL_VERSION": str(PROTOCOL_VERSION),
        "SKILL_REVISION": SKILL_REVISION,
        "INTEGRATIONS": json.dumps(integrations, ensure_ascii=False),
    }

    write_text(task_dir / "task.md", render_template(template_root / "task.md", mapping))
    write_text(task_dir / "journal.md", render_template(template_root / "journal.md", mapping))
    write_text(task_dir / "handoff.md", render_template(template_root / "handoff.md", mapping))
    write_text(task_dir / "manifest.json", render_template(template_root / "manifest.json", mapping) + "\n")

    index_data = write_index_and_active(repo_root)
    if not args.no_ai_task_sync:
        sync_ai_task(repo_root, args.title, args.next_step)

    print(
        json_dump(
            {
                "repo_root": str(repo_root),
                "handoff_root": str(root),
                "task_id": task_id,
                "task_dir": str(task_dir),
                "active_count": len(index_data["active_tasks"]),
            }
        ),
        end="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
