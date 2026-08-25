---
name: mcm-oaward-coach
description: |
  美赛(MCM/ICM)建模辅导与论文协作：解析题目 PDF 与数据集，制定资料/数据检索方案，给出建模路线、验证与敏感性分析设计，按 O 奖论文标准提供结构大纲、图表规划、逐段润色与 LaTeX 排版/编译支持。
  适用于用户提到“美赛/数学建模/MCM/ICM/O奖/Problem A/B/C/题目PDF/数据集”，并提供题目文件路径或链接、数据文件（可缺省）以及自己的草稿/结果时。
metadata:
  language: zh
  compatibility: Python 3.9+; LaTeX (xelatex + latexmk); BibTeX (optional)
  default-template: $MCM_WORKSPACE/MCM_Latex2026
---

# MCM/ICM O 奖论文辅导（Coach）Skill

## 重要边界（必须遵守）

1. **可以协作完成“可编译的 LaTeX 论文草稿 + 可复现代码 + 合规交付物”**：我会把题目拆解、数据处理、建模、验证、图表与英文写作落到项目文件里，并跑通编译；但你必须对最终提交负责（尤其是关键假设、数据来源、数值结果、以及是否使用 AI 的披露），并按官方政策如实填写 **Report on Use of AI Tools**。
2. **不抄袭**：可学习历年 O 奖论文的结构与表达，但不得复制其文字、图表、代码或独特表达；任何使用的外部数据/图表/结论必须可追溯并在文中引用。
3. **不编造**：不编造数据、结果、引用、结论。证据不足时必须标记 TODO 并提示你补充/确认。

## 非谈不可的硬约束（先从题面提取，绝不凭记忆）

> 美赛每年的硬性要求以题面/官方说明为准。本 Skill 的默认做法是：先抽取题面文字（`inputs/problem.txt`），把“页数/交付物/AI 披露/必须包含的部分”写进 `plan/intake.md`，再开工。

必须明确并写进 `plan/intake.md` 的条款：
- 解决方案 PDF **不超过 N 页**（以当年题面/官方说明为准；你本机官方缓存显示当前为 **25 页**，且包含 Summary/目录/参考文献/附录/代码等）
- 论文必须英文、字号至少 12pt、匿名（不得出现姓名/学校等）
- 若使用 AI：必须按政策追加 **Report on Use of AI Tools**（**追加在 25 页主体之后**；通常不计入 25 页主体；以政策/题面为准）

建议先读并对齐（本 Skill 已写了速记）：[references/official-rules.md](references/official-rules.md)

## O 奖对标的“工程化交付物”（缺一不可）

> 借鉴 `research-scaffold` 的“结构冻结→渐进式生成”、`research-units-pipeline-skills` 的“流水线单元化”、`arxiv-paper-writer` 的“门禁+issues 合同”、以及 `knowledge-absorber` 的“真理锚定(verification)”。

项目内必须形成这些文件（让你在医院也能随时接手）：
- `plan/intake.md`：题面拆解 + 硬约束 + 风险清单 + 你需确认的问题
- `plan/constraints.md`：从题面/官方缓存抽取的硬约束（页数/字号/匿名/AI 披露）
- `plan/page_budget.md`：页数预算（确保 ≤ 上限且接近高奖常见信息密度）
- `plan/issues.csv`：任务合同（Research/Data/Model/Viz/Writing/QA 每项可追踪 DONE）
- `data/README.md`：每个数据源的来源/下载日期/口径/用途（外部数据必写）
- `plan/ai_use_log.md`：AI 使用过程日志（便于最终生成 AI Use Report）
- `results/summary.md`：所有关键数字一处汇总（写 Summary/Results 必须从这里取数）
- `paper/main.tex` + `paper/main.pdf`：可编译、结构完整、图表可读、引用可追溯
- `paper/ai_use_report.tex`：按官方格式追加在正文末尾（不计入 25 页主体；以政策为准）

## 引用与资料检索（必须升级：不是 3 篇参考文献就能拿高奖）

基本要求（经验门槛，按题型上下浮动）：
- 至少覆盖 4 类来源：
  1) 题面/官方规则/AI 政策
  2) 领域定义/背景（权威机构/百科/教科书）
  3) 方法依据（论文/书籍/技术报告：如变点检测、HMM/状态空间、runs test 等）
  4) 数据来源（如果你补外部数据）
- 每条“关键结论/关键假设/关键参数”必须能在文中引用到来源（或明确写“我们的假设/我们从数据估计得到”）。

执行方式：
1. 先读你本地笔记：`$MCM_WORKSPACE/美赛`（里面有结构/图表/搜索清单与 O 奖倾向）。
2. 再读 O 奖样本（只学结构与呈现，不抄原文）：`$MCM_WORKSPACE/C`
3. 建立 `paper/references.bib` 并在 `data/README.md` 记录外部数据来源；不允许“编造引用/虚构链接”。
4. 用可验证检索生成 BibTeX（推荐 Crossref DOI 拉取），并把每次检索写入 `plan/citation_registry.jsonl`，避免“凭空写引用”：
   ```bash
   python3 ~/.codex/skills/mcm-oaward-coach/scripts/litsearch_crossref.py \
     --query "<你的关键词>" --rows 8 \
     --out-bib paper/references.bib --registry plan/citation_registry.jsonl
   ```

## Quick Start（建议从脚手架开始）

在你的比赛工作目录里执行（会创建一个可复现项目结构，并把题目 PDF 文本抽取出来）：

```bash
python3 ~/.codex/skills/mcm-oaward-coach/scripts/bootstrap_mcm_project.py \
  --problem-pdf "$MCM_WORKSPACE/2025_MCM_Problem_C.pdf" \
  --data-path "$MCM_WORKSPACE/2025_Problem_C_Data" \
  --oaward-samples "$MCM_WORKSPACE/C" \
  --mcm-notes "$MCM_WORKSPACE/美赛" \
  --latex-template "$MCM_WORKSPACE/MCM_Latex2026" \
  --problem-letter "C" \
  --tcn "<你的TCN>" \
  --out-dir "<你的比赛工作目录>"
```

脚手架会（尽可能）自动生成这些“高奖必备工程件”：
- `plan/page_budget.md`、`plan/issues.csv`、`plan/ai_use_log.md`
- `results/summary.md`
- 若提供 `--mcm-notes` 且其中含官方缓存：`plan/constraints.md`
- 若提供 `--oaward-samples`：`plan/oaward_samples_index.md`
- `paper/main.tex`（包含 `\\label{MainLastPage}` 的页数检查钩子）+ `paper/ai_use_report.tex` 模板

然后把生成的项目路径（脚本输出的 `Project:` 行）发给我，并补充：
- 你的队号（Team Control Number，TCN）
- 你们打算用的核心指标/目标（题目通常会给，也可以你们定义）
- 你们目前已完成的部分（哪怕只有直觉/草图/一段 EDA 也行）

## 默认本地资源（本 Skill 会优先利用）

详情见：[references/local-resources.md](references/local-resources.md)

## 工作流（按 Gate 执行；每个 Gate 都要产出文件）

> 参考了 `research-scaffold` 的“结构冻结/渐进式生成”和 `knowledge-absorber` 的“真理锚定”，并借鉴 `arxiv-paper-writer` 的“门禁 + 计划/问题清单”。

### Gate 0：输入核对（Intake）

目标：把“题目要求 + 可用数据 + 交付物约束”一次性对齐，避免后期返工。

必须做：
0. 若有官方/赛事 **AI 使用政策**（例如你本地缓存的 `Contest_AI_Policy.pdf`），先读取并把“可用范围/必须披露/禁止行为”写入 `plan/intake.md` 的开头。
1. 读取题目 PDF，抽取并整理：
   - 子问题列表（2–5 个）
   - 明确的输入/输出/指标/约束
   - 评分点（若题面/官方说明提到）
2. 盘点数据：
   - 题目自带数据（文件清单、字段字典、缺失情况）
   - 你提供的外部数据（来源、时间范围、口径）
3. 若缺数据：生成 **Data Gap List** + **数据检索计划**（见 Gate 1）

产出（写入项目内）：
- `plan/intake.md`：题目拆解 + 数据清单 + 缺口列表 + 你需要回答的 5–10 个关键问题
- `plan/constraints.md`：官方硬约束（从题面/官方缓存抽取；页数/字号/匿名/AI）
- `plan/page_budget.md`：页数预算（让“信息密度/证据链/图表数量”对标高奖）
- `plan/issues.csv`：任务合同（每项都有 DONE 标记，避免“写一半发现漏题”）
- `plan/ai_use_log.md`：AI 使用日志（用于生成最终 AI Use Report）
- `plan/oaward_samples_index.md`：本地 O 奖样本清单（只学结构与呈现）

### Gate 1：数据与证据（Data + Evidence / Truth Anchoring）

目标：把所有“关键事实”落到可核查的数据/文献上，避免空转与幻觉。

流程：
1. 对每个子问题列出“必须让评委信服”的 3 类证据：
   - 领域背景/定义（权威解释）
   - 数据与参数（可下载/可复核）
   - 方法依据（类似问题的经典模型/论文/报告）
2. 缺数据时：
   - 先给出 3–5 个候选权威来源（gov/org/edu 优先）
   - 下载后做字段对齐、口径说明、缺失处理策略
3. 形成 `data/README.md`：每个数据源一行（来源、下载日期、链接、用途、注意事项）

产出：
- `data/README.md`
- `analysis/01_eda.ipynb`（或 `analysis/01_eda.py`）：最小 EDA（分布/趋势/相关/缺失）
 - `plan/citation_registry.jsonl`：检索到的 DOI/来源记录（避免“编造引用”）

最低 EDA 交付（建议 4–6 张图 + 2 张表）：
- 数据概览表（行数/列数/缺失率/基本统计）
- 关键变量分布图、趋势图、相关性/关系图
- 至少 1 张“对后续模型选择有决定作用”的图（不是装饰图）

### Gate 2：建模路线选择（Model Ladder）

目标：不要一上来“堆模型”，而是建立从 Baseline → Improved → Final 的模型阶梯。

要求：
1. 至少提出 2 条路线（A 方案偏可解释/稳；B 方案偏创新/性能），并给出选择理由。
2. 明确：
   - 决策变量、目标函数、约束
   - 训练/校准方式（若需要）
   - 验证方案（对照、交叉验证、外部基准、合理性检验）

产出：
- `plan/model_plan.md`：路线对比表 + 最终选择 + 风险与备选

### Gate 3：实现与结果（Implementation + Results）

目标：让结果“可复现、可解释、可对比”。

要求：
1. 代码可复现：固定随机种子、记录版本、输入输出路径明确。
2. 结果必须定量化：每个子问题至少 1–2 个核心指标。
3. 至少做一个：敏感性分析 / 稳健性分析 / 情景分析（O 奖常见加分项）。

产出：
- `analysis/02_model.ipynb`（或 `.py`）
- `figures/`：可直接进论文的高分辨率图（建议 PDF/SVG/PNG300dpi）
- `results/metrics.json`（或 `results/summary.md`）：关键指标汇总

### Gate 4：写作协作（Structure Freeze → Co-write）

目标：按 O 奖论文的“评审阅读路径”组织信息，**Summary 第一页决定生死**。

规则：
1. 先冻结大纲（一级/二级标题 + 每节 2–4 条要点 + 计划图表），再进入逐段写作。
2. 我可以帮你把你提供的要点/结果写成英文“竞赛论文风格”的段落，并做逻辑与表达优化；
   但你需要对关键假设、最终结论与数值结果负责并确认。
3. 严格对齐题目每个子问题：每一问都要在正文和结论里“点名回答”。

产出：
- `paper/outline.md`（基于 templates/outline.md）
- `paper/main.tex`：在 LaTeX 模板内落地的章节结构（先骨架后内容）

写作完成后的可选增强：
- 使用 `latex-rhythm-refiner` 对 `paper/main.tex` 做节奏与冗余优化（该 Skill 会保留引用与语义）。

### Gate 5：排版与交付（LaTeX + QA）

目标：主解决方案 **≤ 题面上限页数**（常见 25 页；以题面为准）、图表清晰、引用规范、编译无错误；AI Use Report 按政策追加且不计入上限（以题面/政策为准）。

检查清单：
- Summary 是否 1 页且包含：问题一句话、方法框架、关键假设、**2–4 个定量结果**、结论建议、稳健性/局限。
- 图表是否“每张图回答一个问题”，正文是否逐一引用。
- Notation/Assumptions 是否清晰、单位一致。
- Strengths & Weaknesses 是否诚实且有补救方案。
- 参考文献/数据来源是否可追溯。

产出：
- `paper/main.pdf`
- `paper/compile.log`（若有）

强制 QA（不通过就不算完成）：
- 页数检查：主解决方案页数 ≤ 上限（AI Use Report 另算）
- 题目 bullet 覆盖：每个 bullet 在正文与结论里都“点名回答”
- 引用检查：关键结论/关键外部数据都有来源；无“编造引用”
- 图表检查：每张图都有结论型 caption；正文必须引用每张图

常见环境问题（TeX Live 安装较精简时）：
- 若 `xelatex` 报缺包（如 `appendix.sty` / `paralist.sty` / `multirow.sty` / `environ.sty` / `trimspaces.sty` / `berasans.sty`），可用 **用户模式**安装（不需要管理员权限）：
  ```bash
  tlmgr init-usertree
  tlmgr --usermode install appendix paralist multirow environ trimspaces bera
  ```

## 质量目标（O 奖对标，不做承诺）

详见：[references/oaward-quality-gates.md](references/oaward-quality-gates.md)

## 交互约定（你说什么，我做什么）

- 你给“题目 PDF + 数据路径/链接 + 当前进度”，我先产出 `plan/intake.md` + 任务拆解 + 风险清单。
- 你给“模型选择 + 关键结果（数字/图）”，我帮你把对应章节写成英文并排版进 LaTeX。
- 你给“草稿 tex / md”，我做逐段润色、逻辑一致性检查、图表/符号/单位一致性修复，并给出可执行修改。

## 常用脚本

- 抽取题目 PDF 文本：
  ```bash
  python3 ~/.codex/skills/mcm-oaward-coach/scripts/extract_pdf_text.py \
    --pdf "/path/to/problem.pdf" --out "/path/to/problem.txt"
  ```
- 一键创建项目结构（含 LaTeX 骨架与题面抽取）：见 Quick Start

- 生成页数预算（默认 25 页主体，建议包含 TOC）：
  ```bash
  python3 ~/.codex/skills/mcm-oaward-coach/scripts/create_page_budget.py \
    --out plan/page_budget.md --page-limit 25 --include-toc
  ```

- 生成任务合同（issues.csv）：
  ```bash
  python3 ~/.codex/skills/mcm-oaward-coach/scripts/create_issues_csv.py \
    --out plan/issues.csv --problem-letter C
  ```

- 从官方缓存抽取硬约束（可选，但强烈建议）：
  ```bash
  python3 ~/.codex/skills/mcm-oaward-coach/scripts/extract_official_constraints.py \
    --out plan/constraints.md \
    --instructions-html "$MCM_WORKSPACE/美赛/来源/mcm_instructions.html" \
    --ai-policy-pdf "$MCM_WORKSPACE/美赛/来源/Contest_AI_Policy.pdf"
  ```

- 页数检查（推荐在 LaTeX 里放 `\\label{MainLastPage}`，用于检查“主体 ≤ 25 页”）：
  ```bash
  python3 ~/.codex/skills/mcm-oaward-coach/scripts/check_page_limit.py \
    --pdf paper/main.pdf --aux paper/main.aux --limit 25
  ```

- Crossref 拉取可验证 BibTeX（避免“编造引用”）：
  ```bash
  python3 ~/.codex/skills/mcm-oaward-coach/scripts/litsearch_crossref.py \
    --query "change point detection CUSUM review" --rows 8 \
    --out-bib paper/references.bib --registry plan/citation_registry.jsonl
  ```

- 索引本地 O 奖样本（只学结构/呈现，不抄原文）：
  ```bash
  python3 ~/.codex/skills/mcm-oaward-coach/scripts/index_oaward_samples.py \
    --samples-dir "$MCM_WORKSPACE/C" --out plan/oaward_samples_index.md
  ```
