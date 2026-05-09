# Agent Handoff Protocol v1

## 目标

`agent-handoff` 不追求沉淀一整套项目知识库，而追求三件事：

1. 当前任务是否还能被快速接手；
2. 事实源是否进入版本控制；
3. 根目录是否长期保持小而稳定。

## 目录协议

消费仓库固定使用：

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

### 根目录约束

- 只允许 `ACTIVE.md`、`index.json`、`tasks/`、`archive/`
- 不允许把截图、产物 JSON、一次性报告直接放在根目录
- 不允许把“当前任务计划”“最新问题总结”另起平行根目录

## task-id 规则

- 格式：`YYYYMMDDHHmm-<kebab-slug>`
- 一个任务只有一个 `task-id`
- 同一事项若被后续任务替代，通过 `manifest.json.supersedes` 表达，不新发明“v2 文件名”

## 文件职责

### ACTIVE.md

人类第一入口，只保留：

- 最后更新时间
- 协议版本
- 当前活跃任务列表
- 每个任务的状态、下一步、主事实文件

不要在这里写长篇背景。

### index.json

机器第一入口。固定包含：

- `protocol_version`
- `skill_revision`
- `generated_at`
- `active_tasks`
- `archived_tasks`

`active_tasks` 与 `archived_tasks` 中的元素应至少包含：

- `task_id`
- `title`
- `status`
- `updated_at`
- `next_step`
- `manifest_path`

### task.md

稳定事实页，固定章节：

- `目标`
- `范围`
- `事实源`
- `关键决策`
- `验收标准`
- `当前状态`
- `下一步`

适合放“当前统一认知”，不适合放流水账。

### journal.md

追加式日志。每次只写：

- 时间
- 动作
- 结果
- 遗留

不要把 journal 写成另一个 summary。

### handoff.md

只回答下一位最关心的几件事：

- `已验证基线`
- `未完成`
- `第一步该做什么`
- `先看哪些文件/命令`
- `风险`

默认要求：

- 明显短于 `task.md`
- 不复述整个任务历史
- 不复制整段日志

### manifest.json

固定字段：

- `task_id`
- `title`
- `status`
- `created_at`
- `updated_at`
- `owners`
- `branch`
- `worktree`
- `truth_sources`
- `next_step`
- `blockers`
- `evidence_paths`
- `related_commits`
- `related_tasks`
- `supersedes`
- `protocol_version`
- `skill_revision`
- `integrations`

#### status 枚举

- `active`
- `blocked`
- `handoff-ready`
- `done`
- `archived`

#### integrations 规则

- 只放运行时辅助信息
- 可以为空对象
- 不要把厂商专属字段塞进协议顶层

## 任务生命周期

### 新任务

- bootstrap 根目录
- 创建 task bundle
- 初始状态默认为 `active`
- 写第一条 journal

### 阶段推进

- 更新 `task.md`
- 追加 `journal.md`
- 更新 `manifest.json.updated_at`
- 重渲染 `ACTIVE.md` 与 `index.json`

### 准备交接

- 刷新 `handoff.md`
- 状态改为 `handoff-ready` 或 `blocked`
- 确保 `next_step`、`truth_sources`、`evidence_paths` 有值

### 完成并归档

- 任务目录移入 `archive/`
- `status=archived`
- 从活跃索引移除

## AGENTS 适配

只认 `AGENTS.md` 中的 `## Agent Handoff Overrides` 区块。允许 key：

- `truth_sources`
- `required_checks`
- `evidence_rules`
- `archive_policy`

未知 key 一律忽略。

## 自我迭代

每次改 skill 本身，都要写 `evolution/` 日志。固定字段：

- `trigger`
- `failure_mode`
- `old_rule`
- `new_rule`
- `affected_artifacts`
- `compatibility_impact`
- `migration_needed`
- `evidence`

### 版本规则

- `protocol_version`：消费者协议 schema 变化时升级
- `skill_revision`：行为、文案、脚本实现变化时升级

### 兼容规则

- 只改行为：不要求迁移旧仓库
- 改 schema：必须提供迁移说明，必要时提供脚本
