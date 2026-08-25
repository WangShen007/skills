# 本地资源索引（默认优先使用）

> 这些路径来自你的本机；本 Skill 在需要时会优先读取它们来对齐风格、格式与质量门槛。

## 1) 历年 O 奖论文样本（学习结构与表达，不可抄袭）

- 2025 C 题 O 奖论文（PDF）：`$MCM_WORKSPACE/C`
  - 用法：抽取目录结构、图表类型、摘要写法套路、Strengths/Weaknesses 组织方式。
  - 禁止：复制其原文段落、图表、代码、独特表述。

## 2) 你的美赛笔记（高分结构/流程/绘图规范）

目录：`$MCM_WORKSPACE/美赛`

建议优先读（按用途）：
- O 奖结构与 Summary：`C题O奖高分模板与结构要点.md`
- 从零到交卷流程与数据搜索：`C题建模流程与资料搜索清单.md`
- O 奖判卷关注点与标准：`O奖要求与C题论文汇总.md`
- 图表风格与偏好：`图表风格与O奖倾向.md`
- 绘图代码模板：`高分美观绘图代码.md`

## 3) 官方/规则缓存（强烈建议 Gate 0 先核对）

目录：`$MCM_WORKSPACE/美赛/来源`

重点文件：
- AI 使用政策（如有）：`Contest_AI_Policy.pdf`
- 各年结果页缓存：`2020_results.html` ~ `2024_results.html`
- 题目结果报告示例：`2024_MCM_Problem_C_Results.pdf`

## 4) LaTeX 模板（产出最终 PDF）

- mcmthesis 模板：`$MCM_WORKSPACE/MCM_Latex2026`
  - 推荐：以本模板生成 `paper/main.tex` 与 `paper/main.pdf`
  - 编译：`latexmk -xelatex -interaction=nonstopmode main.tex`

## 5) 你提供的其它“科研技能库”（可借鉴流程）

这些目录包含结构化写作/检索/QA 的 Skill 或参考资料，可按需借用其“门禁、计划、渐进式生成、校验”思想：
- `research-scaffold`：`$MCM_WORKSPACE/research-scaffold`
- `research-units-pipeline-skills`：`$MCM_WORKSPACE/research-units-pipeline-skills`
- `latex-arxiv-SKILL`：`$MCM_WORKSPACE/latex-arxiv-SKILL`
- `StudyAnalysis-Skills`：`$MCM_WORKSPACE/StudyAnalysis-Skills`
- `content-research-writer`：`$MCM_WORKSPACE/content-research-writer`

