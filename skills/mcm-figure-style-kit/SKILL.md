---
name: mcm-figure-style-kit
description: |
  美赛(MCM/ICM)论文图表风格套件：一键把项目的绘图统一成“O奖倾向”的干净2D论文风（色盲友好配色、统一字体/字号、300dpi/矢量PDF输出、结论型caption检查清单），并提供可复用的常见图表模板（趋势、分布、散点回归、热力图、敏感性tornado、参数表）。
  适用于用户提到“绘图风格/图表美观/O奖图表/论文图/figure模板/Matplotlib/Seaborn”，并希望把图表快速统一成比赛论文风格时。
metadata:
  language: zh
  compatibility: Python 3.9+; matplotlib; seaborn (optional)
---

# MCM 图表风格套件（Figure Style Kit）

## Quick Start（把风格装进你的项目）

```bash
python3 ~/.codex/skills/mcm-figure-style-kit/scripts/install_style.py \
  --project "/path/to/your/mcm_project"
```

它会复制：
- `analysis/plot_style.py`（统一 rcParams + 调色板）
- `analysis/figure_templates.py`（常见图表模板函数）

## 风格原则（高奖共同点）

- 2D、信息密度高、配色少（2–4 色），色盲友好
- 坐标轴必须带单位；图例清楚
- 输出优先 PDF（矢量）；或 PNG 300dpi
- caption 写“结论”（so what），不是只写“图里有什么”

## 参考（你的笔记）

- O奖图表倾向统计：`$MCM_WORKSPACE/美赛/图表风格与O奖倾向.md`
- 可直接复用的绘图代码：`$MCM_WORKSPACE/美赛/高分美观绘图代码.md`
