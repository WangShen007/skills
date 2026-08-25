---
name: skill-orchestrator
description: Unified front-door skill that routes one user request across the right installed skills and returns a single integrated result. Use when the user wants 总控/总调度/PM-style coordination, wants one sentence to drive multiple skills, or needs a task to span research, planning, implementation, review, design, docs, Git, deployment, vault work, or other installed skills without manually switching between them.
---

# Skill Orchestrator

把多个已安装 skills 串成一个轻量总控流程，让用户尽量只说一次需求、少手动切换；当环境支持 subagents 时，优先由总控在背后并行调度，而不是让用户手动来回切换。

## Overview

这个 skill 不替代具体 specialist skills。它负责：

1. 判断任务到底需不需要多 skill
2. 选择最小必要 skill 组合
3. 在可并行时把相关工作拆给 subagents 或 specialist skills
4. 最后输出一份整合后的结果，而不是让用户自己拼接

## Managed Subskills

优先从当前会话里已安装、已可用的 skills 中选择。常见路由：

- 研究 / 最新信息：`search-layer`, `content-research-writer`, `openai-docs`
- 规划 / 项目推进：`project-manager`, `task-management`, `linear`
- 编码 / 实施 / 协作：`team-collaboration-issue`, `git-workflow`, `pr-review`
- 设计 / 文档 / 演示：`graphic-designer`, `canvas-design`, `social-graphics`, `pptx`, `drawio`, `uml`
- 知识库 / Obsidian：`obsidian-cli`, `vault-search`
- 技能本身：`skill-creator`, `skill-installer`

如果用户明确点名某个 skill，优先纳入；如果某个 subskill 缺失，继续使用现有 ones，并明确说明缺口。

更细的选择矩阵见 [references/skill-map.md](references/skill-map.md)。
默认组织与模型建议见 [references/company-preset.md](references/company-preset.md)。

## Composition Model

这个 skill 的“调用其他 skills”方式是：

1. 先决定需要哪些已安装 skills
2. 只打开相关 skill 的 `SKILL.md`
3. 如果环境支持 subagents，则由总控把 sidecar 任务并行分配给 subagents
4. 按这些 skills 的工作流执行
4. 汇总成一个最终答复

注意：

- 没有单独的“skill 依赖调用 API”可用时，也照样按上述方式进行组合
- 没有 subagent 能力时，退化成顺序编排，不中断主流程
- 不要一次加载太多 skill，避免上下文膨胀
- 不要递归调用 `skill-orchestrator` 本身

并行 subagent 规则见 [references/parallel-subagents.md](references/parallel-subagents.md)。
外部设计借鉴见 [references/design-borrowings.md](references/design-borrowings.md)。

## Use When

在这些场景使用：

- 用户说“你来当总控 / 总调度 / PM”
- 用户说“帮我一句话调用多个 skills”
- 用户不想手动在多个 skills 之间切换
- 一个任务天然跨多个阶段，例如：
  - 先调研，再写方案
  - 先查资料，再产出文档 / 代码 / 设计
  - 先拆需求，再执行，再 review
  - 先做项目推进，再整理到任务系统 / 文档 / PR
- 用户只知道目标，不知道该先用哪个 skill

## Decision Logic

### Rule 1: Single-skill first

如果一个 specialist skill 就能稳定完成任务，不要强行升级为多-skill 编排。

### Rule 2: Multi-skill only when it adds value

升级到多 skill 的常见信号：

- 用户明确要求“总控 / 编排 / 一句话调用”
- 任务跨 2 个以上领域
- 任务需要明显分阶段推进
- 需要研究 → 产出 → 审查 这样的链路

### Rule 2.5: Prefer manager + workers over handoff ping-pong

默认采用：

- **总控保留用户对话**
- **worker / subagent 在背后执行**
- **最后统一回收并汇总**

只有当用户明确要切到某个 specialist 持续对话时，才改用 handoff 风格。

### Rule 2.6: Prefer worktree-style isolation for coding workers when available

对于会改代码的多个 worker，优先采用“每个 worker 独立工作区 / worktree / branch”的思路，减少并行冲突。

如果当前环境不支持真实 worktree：

- 仍然保持 **ownership 不重叠**
- 在 brief 中明确文件范围
- 由 manager 负责最后集成

### Rule 3: Research first for fresh or high-stakes tasks

- 涉及“最新 / today / 最近 / 当前状态”时，优先 `search-layer`
- 涉及 OpenAI 产品、模型、API、SDK 时，优先 `openai-docs`
- 涉及高风险判断时，先查再做，不要靠记忆硬答

### Rule 4: Add a review gate when shipping matters

涉及代码改动、PR、团队协作、较大变更时，优先考虑加：

- `pr-review`
- `git-workflow`
- 其他更贴切的 reviewer skill（若已安装）

### Rule 5: Keep the initial working set small

默认最多先选：

- 1 个 primary skill
- 1-2 个 support skills
- 1 个 reviewer skill（可选）

只有在明确需要时再扩展。

### Rule 6: Do not block on subagents unless blocked

如果环境支持 subagents：

- 先判断哪些任务是 **immediate blocking**
- immediate blocking 的关键一步，优先由总控本地完成或明确等待
- 非阻塞 sidecar 任务再分给 subagents
- 不要一 spawn 完就立刻反复等待

## Workflow

### Step 1: Classify the job

先把请求归到一个主类型：

- `research`
- `planning`
- `coding`
- `writing`
- `design`
- `knowledge`
- `mixed`

### Step 2: Choose the minimal skill set

按“主 skill + 支持 skill + 审查 skill”思路选，而不是堆很多 skill。

对于 coding / implementation 类任务，优先套用 [references/company-preset.md](references/company-preset.md) 的默认班底，而不是每次重新发明角色。

### Step 3: Decide local work vs subagent work

先区分：

- **Local now**：当前必须马上推进、否则主流程卡住的工作
- **Parallel sidecar**：能在后台并行完成的研究、实现切片、审查、整理

如果任务适合并行：

- 让总控自己做 `Local now`
- 把 disjoint、边界清晰的 sidecar 任务分给 subagents

### Step 4: Load only the relevant skill instructions

只读取将要使用的 skill 的 `SKILL.md` 和必要 references。  
不要把无关 skill 一起读进来。

### Step 5: Pass compact handoff briefs

给每个 subskill 的任务说明必须简短、明确、可交付。  
使用 [references/handoff-contracts.md](references/handoff-contracts.md) 里的 brief 模板。

### Step 6: Synthesize one integrated result

最终对用户只输出一个整合结果，默认包含：

1. 选用了哪些 skills
2. 为什么这么组合
3. 已完成内容
4. 风险 / 缺口 / 待确认项
5. 下一步建议

如果使用了 company preset，额外说明：

6. 哪些角色被激活
7. 哪些角色未启用以及原因

## Output Template

默认按这个结构输出：

```markdown
## Orchestration

### 1) Chosen workflow
- Primary: ...
- Support: ...
- Review: ...

### 2) Why this route
- ...

### 3) Integrated result
- ...

### 4) Risks / gaps
- ...

### 5) Next step
- ...
```

## Guardrails

- 不要为了“看起来高级”而强行多-skill
- 不要假装使用了并不存在或当前不可用的 skill
- 不要把同一信息重复塞给多个 skill
- 不要在没有必要时做长链路编排
- 不要把紧急阻塞任务无脑外包给 subagents
- 不要在 subagents 之间制造重叠写入范围
- 不要 spawn 很多 worker 却没有明确 ownership
- 不要让多个 coding workers 在同一批里无界地修改相同文件
- 如果用户明确只要某个 skill，就尊重用户偏好
- 如果缺少关键输入，只问最少的问题

## Company preset

当用户想要“像一家公司一样运行”时，优先启用默认班底：

- CEO / PM
- Research
- Frontend
- Backend
- Security
- Ops / SRE
- Reviewer

详细角色、模型、何时启用见 [references/company-preset.md](references/company-preset.md)。

## Invocation Examples

- “用 `skill-orchestrator` 帮我先调研再给出执行方案。”
- “用 `skill-orchestrator` 做总控，把这个需求按研究、实现、review 三段走。”
- “用 `skill-orchestrator` 帮我协调相关 skills，我不想自己切来切去。”
- “用 `skill-orchestrator` 并行开几个 subagents，在背后做，不要让我手动切。”
- “用 `skill-orchestrator` 先查 OpenAI 官方文档，再给我落地代码方案。”
- “用 `skill-orchestrator` 帮我把这个任务从项目规划推进到 PR review。”
