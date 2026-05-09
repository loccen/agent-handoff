# Agent Handoff Overrides

## 目的

项目差异统一写在仓库自己的 `AGENTS.md`，不再为 `agent-handoff` 额外引入独立配置文件。

## 固定位置

只读取这个标题下面的第一个 fenced YAML block：

```md
## Agent Handoff Overrides

```yaml
truth_sources:
  - docs/latest
required_checks:
  - npm test
```
```

如果没有这个标题，视为没有 overrides。

## v1 允许的 key

- `truth_sources`
- `required_checks`
- `evidence_rules`
- `archive_policy`

未知 key 一律忽略。

## 建议格式

### truth_sources

推荐写成字符串列表：

```yaml
truth_sources:
  - docs/latest
  - backend/TESTING.md
```

### required_checks

推荐写成字符串列表：

```yaml
required_checks:
  - npm --prefix frontend run build
  - mvn -f backend/pom.xml clean test
```

### evidence_rules

推荐写成一层 map，value 为字符串或字符串列表：

```yaml
evidence_rules:
  visual_changes:
    - screenshot required
  deployment_changes:
    - remote verification required
```

### archive_policy

推荐写成一层 map：

```yaml
archive_policy:
  require_handoff_before_archive: true
  keep_large_artifacts_out_of_git: true
```

## 解析边界

v1 只保证支持：

- 顶层 scalar
- 顶层 list
- 顶层 map
- map value 为 scalar 或 list

不要在 overrides 里写复杂多层 YAML、锚点、别名或内联对象。
