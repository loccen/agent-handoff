# 2026-05-10 03:01 移除用户包装器假设

- trigger: 用户指出系统级 skill 不应提及其个人自定义包装器
- failure_mode: v1 初稿把特定线程态摘要工具作为可选协作层写入 skill 和脚本，导致系统级协议混入用户环境假设
- old_rule: 允许在 skill 中提及特定线程态摘要工具，并在 bootstrap 时尝试同步
- new_rule: system-level skill 不提及任何用户自定义包装器，不自动探测、不自动同步，只保留纯仓库内 handoff 协议
- affected_artifacts:
  - SKILL.md
  - references/protocol.md
  - scripts/handoff_lib.py
  - scripts/bootstrap_handoff.py
- compatibility_impact: 无 schema 变化；仅移除非通用运行时假设
- migration_needed: false
- evidence:
  - 用户自定义线程态摘要工具不是每个用户、每个仓库都会存在
  - 系统级 skill 应保持跨 agent、跨仓库、跨环境最小假设
