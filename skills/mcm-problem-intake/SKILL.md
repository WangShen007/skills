---
name: mcm-problem-intake
description: |
  美赛(MCM/ICM)开赛读题拆解与项目立项：从题目PDF和数据文件夹自动抽取硬约束(页数/AI/仅用给定数据)、任务拆解(Task A/B/C...)、数据清单与数据字典摘要，生成 plan/intake.md + plan/problem_tasks.md + data/data_map.md + paper/outline.md，帮助团队在前1-2小时把方向钉死。
  适用于用户提到“读题/拆解题目/题目PDF/题面/数据字典/立项/开赛流程”，并提供题目PDF路径与数据文件夹路径时。
metadata:
  language: zh
  compatibility: Python 3.9+; pypdf; PyMuPDF(fitz) + rapidocr_onnxruntime (OCR fallback)
---

# MCM/ICM 读题拆解（Intake）Skill

## 核心目标

在比赛最前面，把三件事一次性对齐：
1) **题目要你做什么**（子任务+输出）  
2) **你允许用什么**（数据/AI/页数/格式）  
3) **你将怎么交付**（计划文件+大纲+数据地图）

## Quick Start

```bash
python3 ~/.codex/skills/mcm-problem-intake/scripts/problem_intake.py \
  --problem-pdf "/path/to/Problem_C.pdf" \
  --data-dir "/path/to/data_folder" \
  --out-dir "/path/to/project_root"
```

生成的关键文件：
- `inputs/problem.txt`：题面文本（含 OCR 兜底）
- `plan/problem_tasks.md`：题目 bullet 拆解（可直接做 checklist）
- `plan/intake.md`：硬约束 + 风险点 + 你需要团队确认的问题
- `data/data_map.md`：数据文件清单 + data_dictionary 摘要
- `paper/outline.md`：结构冻结模板（先写要点再写正文）

## 使用规范

- **禁止凭记忆写规则**：规则必须从题面/官方缓存里抽取出来（否则很容易写错）
- **先冻结结构**：先把 outline 写成“2–4 要点 + 计划图表”，确认后再写正文
- **不编造数据/引用**：缺什么就写 TODO，并在 `plan/intake.md` 里列“数据缺口/证据缺口”
