# Personal Skills

个人使用的 Agent Skills 集合。

这个仓库只保存可复用的 Skill 源码、说明文档和必要脚本，不保存 API Key、登录凭据、运行缓存、虚拟环境或生成结果。

## 当前收录

### 图像、PPT 与科研图形

- `image-to-editable-ppt`：把图片、扫描 PPT、PDF 或图片型 PPT 还原为对象级可编辑 PPTX。
- `GordenImage2PPTX`：图片型 PPT 的分层复刻与可编辑 PowerPoint 生成。
- `academic-figures-drawer`：生成适合论文的可编辑科研图和 draw.io 图。
- `gpt-image-2-style-library`：GPT Image 风格选择和科研图提示词模板。
- `codex-gateway-imagegen`：通过已配置的图像网关生成或编辑图片。
- `tech-visual-explainer`：生成单文件技术可视化 HTML。

### 论文与科研工作流

- `mcm-figure-style-kit`
- `mcm-citation-compliance`
- `mcm-oaward-coach`
- `mcm-oaward-samples-analyzer`
- `mcm-problem-intake`
- `latex-rhythm-refiner`

### 总控与个人定制

- `skill-orchestrator`：把多个 Skills 串成一个统一入口。
- `personal-management-orchestrator`：个人事务和目标的综合规划入口。

## 使用方式

在 Codex/兼容 Agent 中，把本仓库作为 Skills 目录来源，或将需要的子目录复制到本机的 Skills 目录。调用时直接描述目标即可，例如：

> 使用 `image-to-editable-ppt`，把这张图片转换成可编辑 PPT，并完成 Office 渲染和视觉检查。

每个子目录的 `SKILL.md` 是该 Skill 的入口和使用说明。

## 安全约定

- 不提交 `.env`、认证文件、Token、Cookie、私钥或本地配置。
- 不提交 `node_modules/`、`.venv/`、`venv/`、`__pycache__/` 和大批量生成图片。
- 第三方 Skill 保留其原有 LICENSE、作者和来源信息；使用前应遵守对应许可。
- 处理真实数据时，只把完成任务所需的局部文件交给外部 OCR 或图像模型。
- MCM 技能中的 `$MCM_WORKSPACE` 是你本机的题目/论文工作区，需要按实际路径设置。

## 更新原则

1. 先在本地验证 Skill 的入口、依赖和示例命令。
2. 改动 `SKILL.md` 后同步更新必要的 references、测试和 README。
3. 每次提交说明变更原因、验证方式和是否有兼容性影响。
4. 只把稳定、可复用的版本放入本仓库；临时实验放在单独目录。
