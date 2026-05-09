---
name: agent-handoff
description: Use when a repository needs durable, repo-tracked handoff state for cross-session, cross-agent, or cross-platform work. This skill creates and maintains a minimal `.agent-handoff/` protocol with active task index, per-task handoff bundle, machine-readable manifest, AGENTS.md overrides, and evolution logs so the next agent can continue without reading chat history.
---

# Agent Handoff

为仓库建立一套可追踪、可交接、可机读的 handoff 协议。它解决的不是“如何写很长的工作报告”，而是“让下一个 agent 在不读聊天历史的前提下，能立刻知道现在是什么状态、先做什么、证据在哪”。

默认事实源是仓库内 `.agent-handoff/`。`ai-task` 只是可选的线程态镜像，不是 durable source of truth。

## 什么时候用

在这些场景触发：

- 一个任务需要跨会话接续，不能只靠聊天上下文。
- 一个任务需要被别的 agent、人类工程师或别的平台 agent 接手。
- 你已经感到上下文膨胀，继续把剩余事项留在聊天里会让后续接手越来越模糊。
- 需要把“当前状态、下一步、验证证据、阻塞点”沉淀到版本控制里。
- 仓库还没有统一的 handoff 协议，或现有记录结构已经膨胀成难以搜索的档案堆。

这些情况不要优先用它：

- 一次性问答，没有后续接手需求。
- 单条 shell 命令或临时草稿，不需要 repo-tracked 历史。
- 项目已经有更强、更明确的 handoff 协议，并且它与你当前任务直接冲突。

## 核心规则

- 先读 `AGENTS.md`。如果存在 `## Agent Handoff Overrides`，只认其中允许的 key。
- `.agent-handoff/ACTIVE.md` 是人类第一入口，`.agent-handoff/index.json` 是机器第一入口。
- 一个任务只对应一个 task bundle，不要把同一件事拆成散落的多个说明文件。
- `handoff.md` 必须明显短于 `task.md`。它只回答“下一位先看什么、先做什么、哪些已经验证过”。
- 图片、截图、JSON 证据不能散落在 `.agent-handoff/` 根目录，只能进对应任务的 `evidence/`。
- 任务完成且无需继续交接时，把任务目录移入 `archive/`，不要把旧任务长期留在 `tasks/`。
- 如果环境里有 `ai-task`，可以同步一份极短 brief；如果没有，也不得影响主协议。

## 默认工作流

### 1. 进入仓库先判定是否需要 bootstrap

- 先读 `AGENTS.md`
- 再看 `.agent-handoff/ACTIVE.md`
- 若 `.agent-handoff/` 不存在，或存在但结构不全，用 `scripts/bootstrap_handoff.py`
- 若已经存在，只处理当前任务 bundle，不新造平行目录

### 2. 每个任务固定维护一组文件

默认目录：

```text
.agent-handoff/
├── ACTIVE.md
├── index.json
├── tasks/
│   └── <task-id>/
│       ├── task.md
│       ├── journal.md
│       ├── handoff.md
│       ├── manifest.json
│       └── evidence/
└── archive/
```

字段和职责的完整定义见 [references/protocol.md](references/protocol.md)。

### 3. 阶段推进时只做最小同步

- 稳定事实写到 `task.md`
- 过程动作追加到 `journal.md`
- 交接前刷新 `handoff.md`
- 任何状态变更后，运行 `scripts/render_active_index.py`
- 交付前运行 `scripts/validate_handoff.py`

### 4. AGENTS 适配只走一个入口

只读取 `AGENTS.md` 中这个区块：

```md
## Agent Handoff Overrides

```yaml
truth_sources:
  - docs/latest
required_checks:
  - npm test
```
```

允许 key、解析规则和忽略策略见 [references/agents-overrides.md](references/agents-overrides.md)。

### 5. 任务结束时归档，而不是继续堆文档

- 不再需要继续 handoff 的任务，移动到 `archive/`
- `manifest.json` 的 `status` 改为 `archived`
- 重新渲染 `ACTIVE.md` 与 `index.json`
- 必要时再同步一条极短 `ai-task clear`

## 脚本与模板

优先使用这些资源：

- `scripts/bootstrap_handoff.py`：创建 `.agent-handoff/` 和首个任务 bundle
- `scripts/render_active_index.py`：根据 manifest 重建 `ACTIVE.md` 与 `index.json`
- `scripts/validate_handoff.py`：校验目录、字段、索引和根目录膨胀
- `scripts/extract_agents_overrides.py`：从 `AGENTS.md` 提取允许的 overrides
- `templates/`：所有协议模板

## 自我迭代规则

这个 skill 允许直接自改，但不能无痕自改。

每次发现 skill 缺点时：

1. 直接修改 skill 源码仓库，而不是只改消费仓库副本。
2. 同步新增一份 `evolution/YYYYMMDDHHmm-<slug>.md`。
3. 只改行为、不改 schema 时，只更新 `skill_revision`。
4. 改动消费者协议时，才升级 `protocol_version`，并给出迁移说明。

演进日志字段和判定规则见 [references/protocol.md](references/protocol.md)。

## 交付前检查

- 下一个 agent 只读 `ACTIVE.md + handoff.md + manifest.json`，能不能知道先做什么？
- 根目录里有没有散落的截图、JSON、临时报告？
- `handoff.md` 是否比 `task.md` 短得多？
- `manifest.json` 是否补齐了 `status`、`next_step`、`truth_sources` 和 `evidence_paths`？
- `ACTIVE.md` 与 `index.json` 是否已经重渲染？
- 如果改了 skill 自己，是否已经写了 `evolution/` 日志？
