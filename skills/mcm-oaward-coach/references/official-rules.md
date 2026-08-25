# 官方硬约束速记（从本机缓存提取，写作/排版必读）

> 目的：避免“硬伤”。以官方当年规则为准；这里给出你本机缓存里最关键的几条，并标注来源位置，方便快速核对。

## 1) 25 页上限：算哪些内容？

来自（本机缓存）：`$MCM_WORKSPACE/美赛/来源/mcm_instructions.html`

- 25 页上限适用于**整个提交**，包含 Summary Sheet、Solution、Reference List、Table of Contents、Notes、Appendices、Code，以及题目特殊要求（原文在 HTML 里“Changes for 2026”条目附近）。
- 论文必须是英文 PDF，字体至少 12pt；且必须在 25 页内（在“Contest Rules”条目附近）。

## 2) AI Use Report：是否计入 25 页？

来自（本机缓存）：`$MCM_WORKSPACE/美赛/来源/Contest_AI_Policy.pdf`（v102025）

- 主体解决方案仍受 25 页限制。
- 若使用 AI 工具：在报告末尾追加一个新章节 **Report on Use of AI Tools**。
- 该章节**没有页数上限**，并且**不计入** 25 页主体解决方案页数。
- 需要在正文中用 inline citations + reference section 说明 AI 工具使用，并在 AI Use Report 里按示例披露（可能要求粘贴 exact query + complete output）。

## 3) 写作动作上的“硬约束落地”

建议把这些约束写进项目文件并自动检查：

- `plan/constraints.md`：用脚本从缓存/题面抽取关键条款
- `plan/page_budget.md`：把 25 页拆到各章节，避免后期爆页
- `paper/main.tex`：在 AI Use Report 之前插入 `\\label{MainLastPage}`，用于自动检查“主体 ≤ 25 页”

