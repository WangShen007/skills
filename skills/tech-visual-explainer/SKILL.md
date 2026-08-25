---
name: tech-visual-explainer
description: 创建手绘风(Excalidraw 质感)、单文件、联网增强 + 断网优雅降级的技术可视化 HTML 页面(rough.js + 手写字体 + 纯 CSS 过程动画),用于讲解系统架构、流程机制、状态转换、模块关系和数据流,支持原理过程的动态演示。当用户需要可视化地解释技术原理、展示架构设计、说明工作流程、演示运行机制或对比技术方案时使用。
---

# 技术可视化讲解

创建专业的交互式技术可视化。**技术解释能力第一,视觉表现第二**。

产物是**单文件 HTML**,默认手绘风:rough.js 手绘图元 + 霞鹜文楷手写字体 + CSS 编排动画(draw-on 描边入场、数据流动粒子、步骤/过程演示)。联网呈现完整效果;**断网自动降级**为干净的静态图——内容与交互不丢,只丢手绘质感,任何机器双击即开。

## 两个模板怎么选

| 模板 | 风格 | 适用 |
|---|---|---|
| `assets/template-sketch.html`(默认) | 手绘纸面风,CDN 增强 + 离线降级 | 绝大多数讲解场景 |
| `assets/template.html` | 专业极简深色风,严格零网络依赖 | 用户明确要求正式风格或完全离线环境 |

## 工作流

1. **选型**:按下方「可视化类型选择」确定表现形式与布局。
2. **复制模板**:`cp <本 skill 目录>/assets/template-sketch.html <输出路径>.html`。模板是设计 token 与渲染 helpers 的唯一来源,禁止从零手写脚手架。
3. **填充内容**:替换模板中的示例数据(`nodes`/`edges`/`steps`)与 `renderDiagram` 组装逻辑。进阶模式(时序图、hover 聚焦、自动布局、GSAP 编排)查 [references/patterns.md](references/patterns.md);设计细则查 [references/design-system.md](references/design-system.md)。
4. **自检**(headless Chrome):
   - 联网观感:`google-chrome --headless --disable-gpu --screenshot=<png> --virtual-time-budget=15000 "file://<绝对路径>"`
   - 结构确定性:追加 `--force-prefers-reduced-motion`(跳过动画,截图必然是终态)
   - 断网降级:再追加 `--host-resolver-rules="MAP * ~NOTFOUND"`
   - 无残留示例数据与【填写】【替换】占位符;核对质量清单
   - 完成后用 `xdg-open <文件>`(Linux)/`open <文件>`(macOS)为用户打开
   - 注意:headless 下「断网 + 动画」组合截图偶发不定(虚拟时钟伪影,真实浏览器无此问题),验证断网降级必须配合 reduced-motion 标志。

## 通用性工程规则(硬性)

- **状态性视觉必须由 CSS 驱动**(class 切换 + transition/animation):高亮、弱化、面板内容、入场终态。CSS 由时钟驱动,在 headless、后台标签页、rAF 受限环境都保证到达终态;JS 动画库只能做锦上添花,其失败不得影响信息表达。
- **CDN 依赖必须多源 + 超时 + 降级**:模板的 `loadScript` 依次尝试 jsDelivr → unpkg,6s 超时;rough.js 加载失败时 helpers 自动退化为干净几何图形。新增依赖必须遵守同一模式,并实测断网路径。
- **允许的 CDN 域**:`cdn.jsdelivr.net`(首选,国内外均可达)、`unpkg.com`(备用)。禁止 Google Fonts(国内不可达)、禁止 Babel/React 运行时(3MB 级转译是打开慢的根源)。
- **字体**:霞鹜文楷 webfont 按 unicode-range 子集懒加载 + `font-display: swap`,首屏不阻塞;字体栈兜底本机楷体。

## 可视化类型选择

| 要解释的内容 | 选用形式 | 关键元素 |
|---|---|---|
| 系统组成与依赖 | 架构图 | 模块节点 + 连接箭头 + 分组区域 |
| 步骤/决策过程 | 流程图 | 有序节点 + 条件分支 + 方向箭头 |
| 层次/职责划分 | 分层模块图 | 水平层 + 模块卡片 + 跨层连接 |
| 状态与转换 | 状态流转图 | 状态节点 + 转换边 + 触发条件标签 |
| 时间顺序交互 | 时序图 | 参与者列 + 生命线 + 消息箭头 |
| 概念/原理解析 | 注释式图示 | 核心图形 + 标注气泡 + 说明文字 |

可组合使用。复杂主题优先用**步骤切换**分解为可理解的阶段。

## 布局参考

- **全景式**(架构总览):标题 → 主图 → 说明卡片行,用 `.card-grid`
- **步骤式**(流程/机制讲解,模板默认):stepper + 图表区 | 说明面板,用 `.layout-split`
- **对比式**(方案对比):两图并排 + 差异说明,用 `.layout-compare`

## 设计核心原则

1. **每个元素必须帮助理解** — 无解释价值的装饰一律删除
2. **手绘感服务于亲和力,不牺牲信息密度** — 笔触是质感,不是噪音
3. **动效只做两件事:演示原理过程 + 指示当前状态** — 位移/形变插值、逐项揭示、数据流动是演示;激活/弱化是状态指示。持续性装饰动效(边框抖动、循环发光、遮字高亮)干扰阅读,一律不用;内容不适合动态展示就保持静态
4. **渐进揭示** — 用步骤/交互引导读者逐层理解复杂概念
5. **一致性** — 同一页面配色、字体、间距、动效参数、seed 策略严格统一

## 动效词汇(全 CSS 实现,模板已内置)

| 动效 | 用途 | 实现 |
|---|---|---|
| draw-on 描边入场 | 图形像被笔画出来 | `.draw-in` + `pathLength=1`,0.55s,15ms/元素 stagger |
| 数据流动粒子 | 演示当前步骤连线上的数据流向 | `flowDots`/`syncFlows`,CSS offset-path 循环,goStep 自动同步 |
| 步骤连线重放 | 切步骤时活跃连线重画一遍 | 移除/重加 `.draw-in`(见 goStep) |
| 过程演示 | 原理动态推演:位移/形变插值、逐项揭示、自动播放 | class/style 切换 + CSS transition,见 patterns.md「过程演示动画」 |
| 激活强调 | 当前步骤节点笔画加粗 | `.node.is-active .shape` stroke-width 1.6→2.6 |
| 聚焦弱化 | 非当前元素退后 | `.is-dimmed` opacity 0.22,0.3s |
| 内容入场 | 页面区块 stagger | `.anim-in` + `--i`,60ms 间隔 |

**禁止**:边框持续抖动(boil 类效果)、遮挡文字的色块高亮、旋转、大幅位移(>20px)、循环发光、一切无信息量的装饰动画。`prefers-reduced-motion` 全量降级已内置(过程演示退化为静态终态)。GSAP 等 JS 编排库仅作进阶可选(见 patterns.md),且必须遵守「CSS 保底终态」规则。

## 配色语义(变量在模板 `:root` 定义,禁止另写 hex)

`--blue` 核心/主流程 · `--teal` 数据/存储 · `--amber` 用户/入口 · `--purple` 外部/第三方 · `--red` 错误/异常 · `--ink`/`--ink-soft`/`--ink-faint` 墨色三级 · `--paper`/`--paper-alt` 纸面。衍生透明度用 `color-mix()`。深色黑板主题:`<html data-theme="chalk">`。

## 质量清单

- [ ] 每个视觉元素服务于技术解释
- [ ] 断网打开内容完整(降级路径实测过)
- [ ] 配色/字体全部来自模板 token,未新增 hex
- [ ] SVG 元素有语义化 class 与 data-id;同一元素 seed 固定(boil 帧除外)
- [ ] 交互有信息反馈(步骤切换、聚焦弱化、hover)
- [ ] 动效只用于过程演示与状态指示,无装饰性动画(无边框抖动、无遮字高亮)
- [ ] 状态性视觉全部 CSS 驱动,JS 库失败不影响阅读
- [ ] 数据定义与渲染逻辑分离,无残留示例内容
- [ ] SVG viewBox 自适应,页面适配 768px+ 宽度
- [ ] 信息密度高但不拥挤

## 参考文件

| 文件 | 何时读 |
|---|---|
| [assets/template-sketch.html](assets/template-sketch.html) | 默认必用 — 复制为输出文件起点 |
| [assets/template.html](assets/template.html) | 零依赖/正式风格场景的备选模板 |
| [references/patterns.md](references/patterns.md) | 时序图、聚焦、自动布局、GSAP 进阶编排 |
| [references/design-system.md](references/design-system.md) | token 语义、排版、rough 参数、动效细则 |
