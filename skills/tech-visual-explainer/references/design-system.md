# 设计系统细则

Token 色值以各模板 `:root` 定义为**唯一来源**,本文件只约定用法。衍生色一律 `color-mix(in srgb, var(--x) N%, transparent | var(--paper-alt))`,禁止手写 hex。

## 手绘模板(template-sketch.html,默认)

### Token 语义

| 变量 | 用途 |
|---|---|
| `--paper` / `--paper-alt` | 纸面底色 / 卡片、面板、图表底 |
| `--ink` / `--ink-soft` / `--ink-faint` | 主笔触与正文 / 次要文字与默认连线 / 弱注释与分组框 |
| `--line` | 点阵坐标纸、虚线分隔 |
| `--blue` `--teal` `--amber` `--purple` `--red` | 分类色,见下表 |
| `--wobble-a` / `--wobble-b` | 手绘边框的不对称圆角(HTML 组件用,交替使用避免重复感) |
| `--font-hand` | 手写字体栈:LXGW WenKai(webfont)→ 本机楷体 → cursive |
| `--font-mono` | 代码/等宽场景,系统 mono 栈 |
| `--ease` | 统一缓动 |

### 模块分类配色

| 类别 | 变量 | 典型用途 |
|---|---|---|
| 核心/主要 | `--blue` | 核心模块、主流程路径 |
| 数据/存储 | `--teal` | 数据库、缓存、映射表 |
| 用户/入口 | `--amber` | 用户、客户端、API 入口 |
| 外部/第三方 | `--purple` | 外部服务、远端节点 |
| 错误/降级 | `--red` | 错误处理、熔断降级 |

同一张图同类模块同色。分类色经 `nodeBox({ color: 'var(--teal)' })` 传入(落到 CSS 变量 `--c`),激活态边框/标签/荧光条自动使用。

### rough.js 参数约定(模板 `SKETCH` 常量)

| 参数 | 值 | 说明 |
|---|---|---|
| roughness | 1.2(连线 ≤1.0) | 更大显潦草,更小显死板 |
| bowing | 1.1 | 线条弯曲度 |
| seed | `hashId(id)` 派生 | **确定性**:同一元素每次渲染形状一致 |
| strokeWidth | 1.6 | 与 HTML 组件 1.6px 边框一致 |
| hachure 填充 | fillWeight 0.5 / gap 8 / opacity 0.3 | 节点淡斜线阴影,克制 |

颜色不传给 rough(保持属性 `#000`),由 CSS 按 class 覆盖——这是主题切换与状态高亮不需要重渲染的关键。

### 排版

| 层级 | 规格 |
|---|---|
| 页面标题 `h1` | 27px / 700 |
| 节标题 `h2` | 20px / 700 |
| 小标题 `h3` | 16px / 700 |
| 正文 | 15px,`--ink-soft` |
| 卡片/面板正文 | 13.5px,`--ink-soft` |
| 节点标签 / 副标签 | 15px 700 / 12px |
| 连线标签 | 12.5px,激活时转分类色加粗 |
| 分组标题 | 12px / 700 / letter-spacing 0.08em |

手写字体比无衬线体视觉偏小,同层级字号比常规设计大 1-2px,已体现在上表。

### 间距与组件

- 页面容器 max-width 1120px,内边距上 40 / 侧 24 / 下 64
- 节点默认 150×52(手绘抖动需要比直线风格更多留白,节点间距 ≥90px)
- 卡片/面板边框 1.6px `--ink` + wobble 圆角;`.card:nth-child(even)` 用 `--wobble-b` 交替
- 点阵背景 26px 网格,`--line` 色 0.8px 圆点

### 主题

- 默认 `data-theme="paper"`(米白纸面)
- `data-theme="chalk"`(深色黑板)已定义变量覆盖,颜色为提亮版分类色;因 rough 颜色走 CSS,切主题无需重渲染

## 动效参数(全 CSS)

| 场景 | 类/机制 | 参数 |
|---|---|---|
| draw-on 入场 | `.draw-in` + `pathLength=1` | 0.55s,`--di`×15ms stagger,fill both |
| 文本入场 | `.fade-el` | 0.35s,跟随图形之后 |
| 流动粒子 | `.flow-dot` + CSS offset-path | 2.2s linear 循环,2 粒/边,r=3.5,首尾 12% 淡入淡出;只放当前步骤活跃边,`@supports` 包裹不支持则隐藏 |
| 激活强调 | `.node.is-active .shape` | stroke-width 1.6→2.6,0.2s |
| 过程演示 | class/style 切换 + transition | 位移步进 transform 0.45s;形变插值 transform 0.8s;详见 patterns.md「过程演示动画」 |
| 聚焦弱化 | `.is-dimmed` | opacity 0.22,0.3s |
| 面板切换 | `.panel-swap` | fade-in-up 0.3s |
| 区块入场 | `.anim-in` + `--i` | 0.4s,60ms stagger |

**严格禁止**:边框持续抖动(boil 类)、遮挡文字的色块高亮、旋转、>20px 位移、循环发光、无信息量装饰动画。`prefers-reduced-motion` 降级已内置(动画全关,状态瞬时到位)。

## 极简模板(template.html,零依赖备选)

深色专业风,token(`--bg`/`--surface`/`--accent` 等)与图元规范见模板内定义;动效为 CSS 入场 stagger + class 切换过渡 + `.flow-line` 流动虚线。适用:完全离线环境、正式汇报场合。浅色用 `data-theme="light"`。
