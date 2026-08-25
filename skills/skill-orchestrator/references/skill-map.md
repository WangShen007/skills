# Skill routing map

用这个表把请求映射到最小必要 skill 组合。优先少而精，不要一口气全上。

## General rules

1. 先选 **1 个 primary skill**
2. 再加 **0-2 个 support skills**
3. 只有在交付质量明显受益时，再加 **1 个 reviewer skill**

## Routing matrix

### 1) Latest facts / external research

- Primary: `search-layer`
- Support: `content-research-writer`
- Special case: 如果主题是 OpenAI 产品 / API / SDK，改用 `openai-docs`

Use when:
- 最新进展
- 对比调研
- 找资源 / 文档 / 官网 / 实现方式

### 2) Research -> writing / report / memo

- Primary: `content-research-writer`
- Support: `search-layer`

Use when:
- 调研后要写总结
- 调研后要写长文、方案、汇报

### 3) Planning / scope / task breakdown

- Primary: `project-manager`
- Support: `task-management`, `linear`

Use when:
- 立项
- 拆里程碑
- 周计划 / 执行板
- 任务分发

### 4) Coding / bugfix / implementation

- Primary: `team-collaboration-issue`
- Support: `git-workflow`
- Review: `pr-review`

Use when:
- 根据 issue 或需求实施
- 修 bug
- 改代码并准备 review

Default roles:
- CEO / PM
- Frontend and/or Backend
- Reviewer
- Security / Ops only when needed

### 5) OpenAI build tasks

- Primary: `openai-docs`
- Support: `team-collaboration-issue`, `search-layer`

Use when:
- 需要最新 OpenAI 官方文档
- 选模型
- SDK / API 迁移
- 代码实现依赖 OpenAI 产品知识

Default control flow:
- sequential: docs → plan
- parallel: implementation lanes when scope is separable
- loop: review / fix / verify

### 6) Design / visual assets

- Primary: `graphic-designer`
- Support: `canvas-design`, `social-graphics`, `pptx`, `drawio`, `uml`

Use when:
- 需要图形资产
- 演示文稿
- 架构图 / UML
- 社媒图 / 封面图

### 7) Obsidian / vault workflows

- Primary: `obsidian-cli`
- Support: `vault-search`

Use when:
- 读写笔记
- 搜 vault
- 更新学习 / 工作知识库

### 8) Skill management

- Primary: `skill-creator`
- Support: `skill-installer`

Use when:
- 创建 skill
- 更新 skill
- 安装或整理 skill

## Good combinations

### Research + implementation

- `search-layer` -> `team-collaboration-issue` -> `pr-review`
- 并行建议：
  - worker A: `search-layer`
  - manager: 同步整理约束
  - worker B: `pr-review` 可在实现后介入

### OpenAI docs + implementation

- `openai-docs` -> `team-collaboration-issue`

### Plan + execute + review

- `project-manager` -> `team-collaboration-issue` -> `pr-review`
- 并行建议：
  - manager: 本地拆计划
  - worker A: implementation
  - worker B: independent review

### Research + write

- `search-layer` -> `content-research-writer`

### Design + slides

- `graphic-designer` -> `pptx`

### Research fan-out

- `search-layer` + `openai-docs`
- 适合多个 worker 各查一个来源，manager 最后汇总

## Bad combinations

- 一上来同时加载 5-8 个 skill
- 明明是单一任务却强行 research + planning + coding + design 全套
- OpenAI 官方问题不用 `openai-docs`，却先去泛搜
- 简单 PR review 还额外拉无关 design / vault skill
