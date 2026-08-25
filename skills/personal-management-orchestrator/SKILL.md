---
name: personal-management-orchestrator
description: Unified personal management orchestrator that combines relationship, time, project, health, habit, and goal skills into one planning workflow. Use when the user asks for 一体化规划, 一键计划, 个人管理总控, or wants one-sentence planning for today/week/month across multiple life domains.
allowed-tools: Read, Write, Edit, Glob, Grep, TaskCreate, TaskUpdate, TaskList, TaskGet
---

# Personal Management Orchestrator

一体化个人管理总控技能：把你已安装的多个子技能串成一个流程，做到“用户一句话 -> 输出完整规划”。

## Use When

- 用户说“帮我一体化规划今天/本周/本月”
- 用户说“我想一句话调用全部个人管理技能”
- 用户要同时覆盖：目标、时间、项目、关系、健康、习惯

## Managed Subskills

- 目标：`goal-tracking`, `goal-setter`
- 时间：`daily`, `weekly`, `time-blocker`, `eisenhower-matrix`
- 项目/任务：`project-manager`, `task-management`
- 人际：`one-on-ones`, `partner-text-coach`
- 健康/习惯：`health-coach`, `fitness-coach`, `goal-analyzer`, `habit-tracker`

If a subskill is missing, continue with available ones and clearly note the gap.

## One-Sentence Invocation Patterns

- “用 personal-management-orchestrator 给我做今天的一体化规划。”
- “用 personal-management-orchestrator 做本周计划，覆盖项目、时间、人际和健康。”
- “用 personal-management-orchestrator 给我一个本月执行框架。”

## Orchestration Workflow

### Step 1: Determine horizon and constraints

Infer scope:
- `today` -> 24h execution plan
- `week` -> weekly execution board
- `month` -> strategic monthly plan

Capture constraints quickly:
- Hard deadlines
- Fixed meetings/classes
- Energy/health constraints
- Relationship commitments

### Step 2: Build five domain briefs

Create compact briefs in this order:

1. **Goal brief** (goal-tracking/goal-setter)
   - Top 1-3 outcomes
   - Success criteria
2. **Project brief** (project-manager/task-management)
   - Active projects
   - Next milestones and tasks
3. **Time brief** (daily/weekly/time-blocker/eisenhower-matrix)
   - Priority ranking
   - Time blocks
4. **Relationship brief** (one-on-ones/partner-text-coach)
   - Key people to follow up
   - Conversations to prepare
5. **Health brief** (health-coach/fitness-coach/goal-analyzer/habit-tracker)
   - Sleep/exercise baseline
   - Minimum health commitments

### Step 3: Synthesize one integrated plan

Produce a single plan with:

1. **One Big Thing**
2. **Top 3 must-do actions**
3. **Time-block schedule**
4. **Project milestones**
5. **Relationship follow-ups**
6. **Health minimums**
7. **Risk + fallback rules**

### Step 4: Output action-ready artifacts

When user agrees, write/update notes in their vault/workspace (if path provided), typically:
- daily/weekly plan note
- task list updates
- relationship follow-up list
- health checklist

## Output Template

Use this compact structure:

```markdown
## 一体化规划（<today/week/month>）

### 1) One Big Thing
- ...

### 2) 三个必须完成
- [ ] ...
- [ ] ...
- [ ] ...

### 3) 时间块
- 09:00-10:30 ...
- 10:45-12:00 ...

### 4) 项目推进
- 项目A: 本期里程碑 ...
- 项目B: 下一步 ...

### 5) 人际关系
- [ ] 跟进 X（目标：...）
- [ ] 准备 1:1 with Y（3个问题）

### 6) 健康底线
- 睡眠 >= ...h
- 运动 ... 次
- 饮食规则 ...

### 7) 风险与兜底
- 风险: ...
- 兜底动作: ...
```

## Practical Defaults

If user gives little context:
- assume horizon = week
- propose 3 priorities max
- use 60/30/10 capacity split:
  - 60% core work/project
  - 30% maintenance/admin/relationship
  - 10% buffer/recovery

For more detail patterns, see [references/skill-map.md](references/skill-map.md).
