---
name: mcm-oaward-samples-analyzer
description: |
  OCR 批量阅读/分析本地美赛(MCM/ICM)高奖(O奖及以上)论文 PDF：抽取 Summary Sheet、目录结构、参考文献与AI披露线索，统计常见章节与写法共性，并生成可复用的高奖写作模板与清单。
  适用于用户提到“阅读/分析 O奖论文/样本论文/PDF文件夹/目录结构/写法共同点/创新点/参考文献/Letter/Memo/绘图风格”，并提供本地 PDF 路径或文件夹路径时。
metadata:
  language: zh
  compatibility: Python 3.9+; OCR (rapidocr_onnxruntime); PDF render (PyMuPDF/fitz)
---

# MCM/ICM O 奖样本论文结构分析（OCR）

> 这是一项“赛前学习/复盘”技能：**只学结构与呈现，不抄袭原文**。

## 你会得到什么

- `out/pages/summary/*.txt`：每篇 O 奖论文第一页 Summary Sheet 的 OCR 文本
- `out/pages/toc/*.txt`：目录页/前几页的 OCR 文本（用于提炼结构）
- `out/pages/tail/*.txt`：末尾页 OCR 文本（参考文献/Letter/Memo/AI Use Report 常在这里）
- `out/2025_oaward_c_report.md`：统计报告（章节/方法关键词/页数等）
- `out/2025_oaward_c_paper_digests.md`：每篇 Summary 的方法标签速览（用于快速分类）

## 重要边界（必须遵守）

1. **不抄袭**：不得复制任何样本文本/图表/代码/独特表达。
2. **只提炼可迁移的东西**：结构、叙事顺序、图表类型、验证方式、写法习惯。
3. **OCR 有误差**：最终以你打开 PDF 目视核对为准；本技能给的是“快速抽样 + 结构统计”。

## Quick Start（推荐命令）

以你本机 2025 C 题 O 奖样本为例（18 篇 PDF）：

```bash
# 1) 抽取关键页（Summary/TOC/Tail）到文本文件，便于逐篇快速阅读
python3 ~/.codex/skills/mcm-oaward-samples-analyzer/scripts/extract_oaward_pages_ocr.py \
  --pdf-dir "$MCM_WORKSPACE/C" \
  --out-dir "$MCM_WORKSPACE/2025_oaward_c_meta/out/pages"

# 2) 生成结构统计报告（耗时较长，适合一次性跑完并可 --resume）
python3 ~/.codex/skills/mcm-oaward-samples-analyzer/scripts/analyze_oaward_pdfs_ocr.py \
  --pdf-dir "$MCM_WORKSPACE/C" \
  --out-dir "$MCM_WORKSPACE/2025_oaward_c_meta/out" \
  --resume

# 3) 从 Summary Sheet 文本生成“每篇方法标签速览”
python3 ~/.codex/skills/mcm-oaward-samples-analyzer/scripts/make_paper_digests.py \
  --summary-dir "$MCM_WORKSPACE/2025_oaward_c_meta/out/pages/summary" \
  --out "$MCM_WORKSPACE/2025_oaward_c_meta/out/2025_oaward_c_paper_digests.md"
```

## 如何把“样本阅读”转化为你能复用的模板（建议做法）

1. 先看每篇 Summary Sheet：记录“框架一句话 + 关键数字 + 区间 + 可信度一句话”
2. 再看目录：把高频章节顺序抄到你自己的 `paper/outline.md`
3. 最后看 tail：学习 References 的构成、是否有 Letter/Memo、AI Use Report 怎么写

你也可以直接结合你的笔记目录：`$MCM_WORKSPACE/美赛`
