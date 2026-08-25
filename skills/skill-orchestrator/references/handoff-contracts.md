# Handoff contracts

给 subskills 的 brief 要短、小、清楚。目标是让每个 skill 只拿到它需要的上下文。

## Brief template

对任一 subskill，优先用这个结构组织任务：

```markdown
## Skill brief
- Why this skill: ...
- Objective: ...
- Inputs / paths: ...
- Constraints: ...
- Expected deliverable: ...
- Done definition: ...
- What not to do: ...
```

## Minimal examples

### 1) search-layer brief

```markdown
## Skill brief
- Why this skill: Need current implementation options.
- Objective: Find official or primary-source guidance for X.
- Inputs / paths: user requirement only
- Constraints: prefer official docs; include dates when freshness matters
- Expected deliverable: concise findings + links + caveats
- Done definition: enough evidence to choose an approach
- What not to do: do not draft final implementation plan yet
```

### 2) project-manager brief

```markdown
## Skill brief
- Why this skill: Need a workable execution plan.
- Objective: Break the task into milestones and next actions.
- Inputs / paths: research findings, user goal, repo path
- Constraints: keep plan small and actionable
- Expected deliverable: milestones, risks, next actions
- Done definition: a plan someone can start executing immediately
- What not to do: do not implement code
```

### 3) team-collaboration-issue brief

```markdown
## Skill brief
- Why this skill: Need implementation in the codebase.
- Objective: Make the required code changes.
- Inputs / paths: repo path, relevant files, plan summary
- Constraints: preserve unrelated changes, test what is touched
- Expected deliverable: changed files, summary, validation notes
- Done definition: requested code path works or blockers are explicit
- What not to do: do not expand scope into unrelated refactors
```

### 4) pr-review brief

```markdown
## Skill brief
- Why this skill: Need an independent quality gate.
- Objective: Review the proposed change set.
- Inputs / paths: changed files, tests, summary of intent
- Constraints: focus on correctness, regressions, maintainability
- Expected deliverable: findings grouped by severity
- Done definition: clear pass/fail or required fixes
- What not to do: do not rewrite the whole implementation unless needed
```

## Integrated answer contract

当多个 skills 都完成后，最后统一对用户输出：

```markdown
## Orchestration

### Selected skills
- ...

### Work completed
- ...

### Decisions / assumptions
- ...

### Risks / blockers
- ...

### Recommended next step
- ...
```

## Escalation rules

- 如果 research 还没收敛，不要直接进入 implementation
- 如果 implementation 范围不清，不要直接进入 review
- 如果 reviewer 发现高风险问题，回退到对应 specialist 而不是硬收尾
