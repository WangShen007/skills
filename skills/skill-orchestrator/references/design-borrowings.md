# Design borrowings

这个文件记录 `skill-orchestrator` 应借鉴的外部设计思想。

不是要求精确复刻，而是提炼可迁移原则。

## From ComposioHQ/agent-orchestrator

借鉴重点：

### 1) One dashboard / one conductor

- 用户不应该手动盯多个 worker
- 总控统一看进度、统一回收结果、统一决定何时需要人工

### 2) Worktree-style isolation

- 多个 coding workers 并行时，应尽量隔离工作空间
- 如果没有真实 worktree，也要在逻辑上做到：
  - branch / scope / file ownership isolation

### 3) Engineering lifecycle, not just chat lifecycle

总控不只做聊天分流，还要考虑：

- CI
- review comments
- merge conflicts
- integration

### 4) Human only when needed

- 默认让 worker 自治完成子任务
- 只在需要裁决、批准、或业务判断时让用户介入

## From Google ADK

借鉴重点：

### 1) Explicit orchestration primitives

任务不要只写成“去协调一下”，而要先判断属于哪种控制流：

- **Sequential**：必须按顺序
- **Parallel**：可以同时执行
- **Loop**：需要反复修正直到满足条件

### 2) Manager is not always the worker

像 ADK 的 workflow agents 一样，总控主要负责控制流，而不是把所有细活自己做完。

### 3) Deterministic control where possible

如果某段流程本来就应该确定：

- 先查官方文档
- 再写计划
- 再实施
- 再 review

那就不要让总控每轮都重新“自由发挥”。

### 4) Compose, don’t overload

复杂系统要靠小 primitive 组合，而不是一个超大 prompt。

## Translation into skill-orchestrator behavior

因此，这个 skill 默认应这样思考：

1. 先判断是 `sequential`、`parallel`、还是 `loop`
2. 再决定是否要启用 company preset 里的哪些角色
3. coding workers 尽量保证 scope isolation
4. manager 保持用户接口与最终汇总权
5. review / security 作为质量门，而不是默认每步都参与

## Quick heuristics

### Use sequential when

- 下一步强依赖上一步结果
- 用户要一个清晰分阶段流程

### Use parallel when

- 子任务彼此独立
- 来源可 fan-out
- 前后端 / research lanes / review lanes 可分离

### Use loop when

- 需要“实现 → 检查 → 修正”
- 需要多轮评估直到通过

## What not to copy blindly

- 不要把平台级重型基础设施要求照搬到轻量 skill
- 不要因为外部项目支持 20 个 agent，就默认你也要开 20 个
- 不要把 UI/dashboard 的存在当作总控设计本身
