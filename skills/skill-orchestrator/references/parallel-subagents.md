# Parallel subagent mode

这个文件定义 `skill-orchestrator` 在支持 subagents 的环境里应该如何工作。

## Default operating model

默认结构：

```text
User
  ↓
Skill Orchestrator (manager)
  ├─ worker A
  ├─ worker B
  └─ reviewer / checker
```

总控负责：

- 理解用户目标
- 先判断控制流属于 sequential / parallel / loop 哪一种
- 决定是否值得并行
- 划分 write scope / responsibility
- 启动 subagents
- 在后台任务进行时继续做不重叠的本地工作
- 最后统一汇总

建议把这三种模式当成默认 primitive：

- **Sequential**：必须按顺序推进
- **Parallel**：多个独立 worker 同时推进
- **Loop**：实现 / 检查 / 修正 反复直到通过

## When to spawn subagents

适合并行的典型场景：

### 1) Research fan-out

- 同时查多个候选方案
- 同时看多个官方来源
- 同时做 feature / product / risk 三条研究线

### 2) Coding split by ownership

- 前端 / 后端 / 文档分开
- 不同文件夹、不同模块、不同测试范围分开
- reviewer 单独做质量门
- 尽量模拟 worktree-style isolation

### 3) Implementation + review overlap

- 一个 subagent 实施
- 一个 subagent 做只读 review / verification
- 总控同步整理结果、准备最终答复

## When not to spawn

不要并行的场景：

- 任务很小，一个 specialist 就能直接完成
- 下一步完全依赖某个结果，主流程会立刻被阻塞
- 任务边界不清，写入范围高度重叠
- 用户只是想要快速单轮答复

## Dispatch policy

启动 subagents 前先写清：

1. `objective`
2. `ownership`
3. `inputs`
4. `constraints`
5. `done definition`

推荐格式：

```markdown
## Worker assignment
- Role: ...
- Objective: ...
- Ownership: files/modules/decision area ...
- Inputs: ...
- Constraints: ...
- Deliverable: ...
```

## Ownership rules

### Coding tasks

- 每个 worker 必须有 **明确文件范围**
- 如果多个 worker 同时改代码，尽量保证 write set 不重叠
- 明确告诉 worker：你不是独自在代码库里，不要回滚别人改动
- 如果环境支持真实 worktree / branch 隔离，优先使用

### Research tasks

- 每个 worker 负责不同问题，不要重复搜索同一件事
- 总控负责去重和综合，不把所有原始结果都直接甩给用户

## Non-blocking behavior

总控不要这样做：

1. 启动 subagents
2. 立刻空等
3. 每几秒轮询一次

总控应该这样做：

1. 先把 sidecar 工作分给 subagents
2. 立刻继续做本地不重叠工作
3. 只有在下一步真的依赖某个 subagent 结果时才等待

## Integration contract

每个 subagent 的返回至少应包含：

```markdown
### Result
- Status: done / blocked / partial
- Summary: ...
- Changed files / key outputs: ...
- Risks / caveats: ...
- Next recommended action: ...
```

## Suggested patterns

### Pattern A: Research → synthesis

- worker A: official docs
- worker B: alternatives / ecosystem
- manager: synthesize and recommend

### Pattern B: Plan → implement → review

- manager: produce plan
- worker A: implement change
- worker B: independent review
- manager: merge findings and decide next step

### Pattern C: Frontend / backend split

- worker A: frontend ownership
- worker B: backend ownership
- worker C: tests or review
- manager: integration summary

### Pattern D: Sequential → parallel → loop

- manager: clarify and plan
- worker wave: parallel execution
- reviewer: inspect outputs
- manager: if needed, run another fix loop

## Fallback

如果当前环境不支持 subagents，按同样结构 **顺序执行**：

- manager 仍然做路由
- 仍然保持最小 skill 集合
- 只是把并行改为顺序，不改变整体交付结构
