---
name: mcm-citation-compliance
description: |
  美赛(MCM/ICM)引用与合规保障：用 Crossref/DOI 生成可验证的 BibTeX，维护 citation_registry.jsonl，检查 references.bib 中 DOI 是否可解析，避免“编造引用”；同时准备 AI 使用披露日志与 Report on Use of AI Tools 模板，确保页数与AI政策合规。
  适用于用户提到“参考文献/引用/BibTeX/防止假引用/AI Use Report/合规/COMAP policy”，并提供 paper/references.bib 或论文项目路径时。
metadata:
  language: zh
  compatibility: Python 3.9+; network access for Crossref API
---

# MCM/ICM 引用与合规（Citations & Compliance）

## 你会得到什么

- `paper/references.bib`：可验证来源（尽量 DOI）
- `plan/citation_registry.jsonl`：每次检索的 DOI/关键词/日期（可追溯）
- `plan/citation_check.md`：DOI 校验报告（哪些可解析/哪些可疑）
- `plan/ai_use_log.md` + `paper/ai_use_report.tex`：AI 披露材料

## Quick Start

### 1) 用 Crossref 拉 BibTeX（推荐从方法类关键词开始）

```bash
python3 ~/.codex/skills/mcm-citation-compliance/scripts/litsearch_crossref.py \
  --query "zero-inflated negative binomial regression" --rows 8 \
  --out-bib paper/references.bib --registry plan/citation_registry.jsonl
```

### 2) 校验 references.bib 里的 DOI 是否真实可解析

```bash
python3 ~/.codex/skills/mcm-citation-compliance/scripts/check_bib_doi.py \
  --bib paper/references.bib --out plan/citation_check.md
```

### 3) AI 披露（如使用 AI）

- 过程记录：`plan/ai_use_log.md`
- 最终报告：`paper/ai_use_report.tex`（追加在 25 页主体后，不计入；以当年政策为准）

## 强制规则

- 不允许“凭空写参考文献/凭空写 DOI”
- 任何关键结论/关键假设/关键参数都必须：要么来自数据估计、要么有可追溯引用、要么明确写为“assumption”
