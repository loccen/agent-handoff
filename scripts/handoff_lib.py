#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

HANDOFF_ROOT = ".agent-handoff"
PROTOCOL_VERSION = 1
SKILL_REVISION = "1.0.1"
ALLOWED_STATUSES = {"active", "blocked", "handoff-ready", "done", "archived"}
ALLOWED_OVERRIDE_KEYS = {
    "truth_sources",
    "required_checks",
    "evidence_rules",
    "archive_policy",
}
ALLOWED_ROOT_ENTRIES = {"ACTIVE.md", "index.json", "tasks", "archive"}
REQUIRED_TASK_ENTRIES = {
    "task.md",
    "journal.md",
    "handoff.md",
    "manifest.json",
    "evidence",
}


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def timestamp_minute() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d%H%M")


def slugify(text: str) -> str:
    lowered = text.strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    lowered = re.sub(r"-{2,}", "-", lowered).strip("-")
    return lowered or "task"


def generate_task_id(title: str) -> str:
    return f"{timestamp_minute()}-{slugify(title)}"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def json_dump(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def render_template(template_path: Path, mapping: dict[str, str]) -> str:
    content = read_text(template_path)
    for key, value in mapping.items():
        content = content.replace(f"{{{{{key}}}}}", value)
    return content


def git_output(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def detect_branch(repo_root: Path) -> str:
    branch = git_output(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    return branch or ""


def detect_default_owner(repo_root: Path) -> list[str]:
    name = git_output(repo_root, "config", "--get", "user.name")
    return [name] if name else []


def extract_override_block_text(agents_path: Path) -> str:
    if not agents_path.exists():
        return ""
    text = read_text(agents_path)
    heading = re.search(r"^## Agent Handoff Overrides\s*$", text, re.MULTILINE)
    if not heading:
        return ""
    tail = text[heading.end() :]
    block = re.search(r"```ya?ml\s*\n(.*?)```", tail, re.DOTALL)
    if not block:
        return ""
    return block.group(1).strip()


def _scalar_value(raw: str) -> Any:
    raw = raw.strip()
    if not raw:
        return ""
    if (raw.startswith('"') and raw.endswith('"')) or (
        raw.startswith("'") and raw.endswith("'")
    ):
        return raw[1:-1]
    lowered = raw.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "null":
        return None
    if re.fullmatch(r"-?\d+", raw):
        return int(raw)
    return raw


def _parse_indented_block(lines: list[str], base_indent: int) -> Any:
    stripped = [line for line in lines if line.strip()]
    if not stripped:
        return {}

    first_indent = len(stripped[0]) - len(stripped[0].lstrip(" "))
    if stripped[0].lstrip(" ").startswith("- "):
        items: list[Any] = []
        for line in stripped:
            indent = len(line) - len(line.lstrip(" "))
            if indent != first_indent or not line.lstrip(" ").startswith("- "):
                continue
            items.append(_scalar_value(line.lstrip(" ")[2:]))
        return items

    parsed: dict[str, Any] = {}
    index = 0
    while index < len(stripped):
        line = stripped[index]
        indent = len(line) - len(line.lstrip(" "))
        if indent < base_indent:
            index += 1
            continue
        key_part, _, value_part = line.strip().partition(":")
        nested: list[str] = []
        index += 1
        while index < len(stripped):
            next_line = stripped[index]
            next_indent = len(next_line) - len(next_line.lstrip(" "))
            if next_indent <= indent:
                break
            nested.append(next_line)
            index += 1
        if value_part.strip():
            parsed[key_part] = _scalar_value(value_part)
        elif nested:
            parsed[key_part] = _parse_indented_block(nested, indent + 2)
        else:
            parsed[key_part] = {}
    return parsed


def parse_override_yaml(text: str) -> tuple[dict[str, Any], list[str]]:
    if not text.strip():
        return {}, []

    lines = [
        line.rstrip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    parsed: dict[str, Any] = {}
    ignored: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        indent = len(line) - len(line.lstrip(" "))
        if indent != 0:
            index += 1
            continue
        key, _, value = line.partition(":")
        nested: list[str] = []
        index += 1
        while index < len(lines):
            next_line = lines[index]
            next_indent = len(next_line) - len(next_line.lstrip(" "))
            if next_indent == 0:
                break
            nested.append(next_line)
            index += 1
        if key not in ALLOWED_OVERRIDE_KEYS:
            ignored.append(key)
            continue
        if value.strip():
            parsed[key] = _scalar_value(value)
        elif nested:
            parsed[key] = _parse_indented_block(nested, 2)
        else:
            parsed[key] = []
    return parsed, ignored


def load_agents_overrides(repo_root: Path) -> tuple[dict[str, Any], list[str]]:
    block = extract_override_block_text(repo_root / "AGENTS.md")
    return parse_override_yaml(block)


def ensure_handoff_root(repo_root: Path) -> Path:
    root = repo_root / HANDOFF_ROOT
    (root / "tasks").mkdir(parents=True, exist_ok=True)
    (root / "archive").mkdir(parents=True, exist_ok=True)
    return root


def normalize_manifest(manifest: dict[str, Any], manifest_path: Path, bucket: str) -> dict[str, Any]:
    task_id = str(manifest.get("task_id", manifest_path.parent.name))
    return {
        "task_id": task_id,
        "title": str(manifest.get("title", task_id)),
        "status": str(manifest.get("status", "")),
        "updated_at": str(manifest.get("updated_at", "")),
        "next_step": str(manifest.get("next_step", "")),
        "manifest_path": str(manifest_path),
        "task_path": str(manifest_path.parent),
        "bucket": bucket,
    }


def collect_manifests(repo_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    root = repo_root / HANDOFF_ROOT
    active: list[dict[str, Any]] = []
    archived: list[dict[str, Any]] = []
    for bucket in ("tasks", "archive"):
        base = root / bucket
        if not base.exists():
            continue
        for manifest_path in sorted(base.glob("*/manifest.json")):
            try:
                manifest = json.loads(read_text(manifest_path))
            except (json.JSONDecodeError, OSError):
                continue
            entry = normalize_manifest(manifest, manifest_path, bucket)
            if bucket == "archive" or entry["status"] == "archived":
                archived.append(entry)
            else:
                active.append(entry)
    active.sort(key=lambda item: item["updated_at"], reverse=True)
    archived.sort(key=lambda item: item["updated_at"], reverse=True)
    return active, archived


def build_index(repo_root: Path) -> dict[str, Any]:
    active, archived = collect_manifests(repo_root)
    return {
        "protocol_version": PROTOCOL_VERSION,
        "skill_revision": SKILL_REVISION,
        "generated_at": now_iso(),
        "active_tasks": active,
        "archived_tasks": archived,
    }


def _render_task_lines(items: list[dict[str, Any]]) -> str:
    if not items:
        return "- 暂无"
    lines = []
    for item in items:
        lines.append(
            f"- `{item['task_id']}` | `{item['status']}` | {item['title']} | 更新于 `{item['updated_at']}` | 下一步：{item['next_step'] or '待补充'}"
        )
        lines.append(f"  - 主事实：`{item['task_path']}/task.md`")
        lines.append(f"  - 交接包：`{item['task_path']}/handoff.md`")
    return "\n".join(lines)


def render_active_markdown(repo_root: Path, index_data: dict[str, Any]) -> str:
    template_path = Path(__file__).resolve().parent.parent / "templates" / "ACTIVE.md"
    archive_preview = index_data["archived_tasks"][:10]
    return render_template(
        template_path,
        {
            "GENERATED_AT": index_data["generated_at"],
            "PROTOCOL_VERSION": str(index_data["protocol_version"]),
            "SKILL_REVISION": index_data["skill_revision"],
            "ACTIVE_SECTION": _render_task_lines(index_data["active_tasks"]),
            "ARCHIVE_SECTION": _render_task_lines(archive_preview),
        },
    )


def write_index_and_active(repo_root: Path) -> dict[str, Any]:
    root = ensure_handoff_root(repo_root)
    index_data = build_index(repo_root)
    write_text(root / "index.json", json_dump(index_data))
    write_text(root / "ACTIVE.md", render_active_markdown(repo_root, index_data))
    return index_data


def validate_manifest_fields(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_keys = [
        "task_id",
        "title",
        "status",
        "created_at",
        "updated_at",
        "owners",
        "branch",
        "worktree",
        "truth_sources",
        "next_step",
        "blockers",
        "evidence_paths",
        "related_commits",
        "related_tasks",
        "supersedes",
        "protocol_version",
        "skill_revision",
        "integrations",
    ]
    for key in required_keys:
        if key not in manifest:
            errors.append(f"manifest 缺少字段：{key}")
    if manifest.get("status") not in ALLOWED_STATUSES:
        errors.append(f"manifest status 非法：{manifest.get('status')}")
    return errors


def relative_to_repo(repo_root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)
