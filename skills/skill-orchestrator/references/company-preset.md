# Company preset

这个文件定义 `skill-orchestrator` 的默认“公司组织架构”。

目标：

- 用户只和一个总控说话
- 其他角色按需在背后工作
- 角色不求多，但求边界清晰

## Default org chart

```text
User
  ↓
CEO / PM (manager)
  ├─ Research
  ├─ Frontend
  ├─ Backend
  ├─ Security
  ├─ Ops / SRE
  └─ Reviewer
```

## Default roles

### 1) CEO / PM

- Responsibility:
  - 理解需求
  - 拆任务
  - 决定顺序 / 并行 / 循环修正
  - 汇总最终结果
- Default model:
  - `gpt-5.4`
- Reasoning:
  - `high`
- Always on:
  - yes

### 2) Research

- Responsibility:
  - 查资料
  - 读官方文档
  - 做方案对比
- Default model:
  - `gpt-5.2`
- Reasoning:
  - `medium`
- Trigger:
  - 最新信息、方案选择、外部资料依赖

### 3) Frontend

- Responsibility:
  - UI、交互、组件、前端改动
- Default model:
  - `gpt-5.3-codex`
- Reasoning:
  - `medium`
- Trigger:
  - 页面、组件、视觉交互、前端 bug

### 4) Backend

- Responsibility:
  - API、服务逻辑、数据流、后端实现
- Default model:
  - `gpt-5.3-codex`
- Reasoning:
  - `high`
- Trigger:
  - 接口、鉴权、服务层、数据库、任务执行逻辑

### 5) Security

- Responsibility:
  - 权限、密钥、攻击面、越权与泄漏风险检查
- Default model:
  - `gpt-5.4`
- Reasoning:
  - `high`
- Trigger:
  - 登录、权限、凭证、外部连接、生产风险

### 6) Ops / SRE

- Responsibility:
  - 部署、CI/CD、脚本、环境变量、监控
- Default model:
  - `gpt-5.3-codex`
- Reasoning:
  - `high`
- Trigger:
  - deploy、pipeline、preview、runtime、ops tooling

### 7) Reviewer

- Responsibility:
  - 独立检查正确性、回归风险、可维护性
- Default model:
  - `gpt-5.1-codex-max`
- Reasoning:
  - `high`
- Trigger:
  - 代码交付前、较大改动后、需要独立质量门时

## Activation rules

### Minimal team

默认只启用：

- CEO / PM

以下角色按需开启。

### Common activation bundles

#### Research task

- CEO / PM
- Research

#### Coding task

- CEO / PM
- Frontend 或 Backend
- Reviewer（视风险）

#### Full-stack change

- CEO / PM
- Frontend
- Backend
- Reviewer

#### Shipping / deployment

- CEO / PM
- Backend
- Ops / SRE
- Reviewer

#### Security-sensitive change

- CEO / PM
- Relevant implementation role
- Security
- Reviewer

## Dispatch rules

### Research

- 可并行 fan-out
- 每个 worker 负责不同问题或不同来源

### Coding

- 尽量按文件夹 / 模块 / worktree 分 ownership
- Frontend 与 Backend 可以并行
- Reviewer 尽量只读，不要和 implementation worker 重叠写入

### Review

- Reviewer 默认在 implementation 之后启动
- 如果任务很大，可在 implementation 期间先做 side review，但不要阻塞主流程

## Output add-on

当启用此 preset 时，在最终答复里补充：

```markdown
### Activated roles
- CEO / PM: ...
- Backend: ...
- Reviewer: ...

### Idle roles
- Security: not needed because ...
- Ops / SRE: not needed because ...
```

## Guardrails

- 不要每次都把所有角色全开
- 不要把“研究员”和“Reviewer”混为一谈
- 不要让两个 coding 角色在同一批里无界修改同一文件
- 不要让 CEO / PM 退化成纯转发器；它必须做汇总和裁决
