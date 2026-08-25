# 进阶模式

以下针对默认手绘模板 `assets/template-sketch.html`(零依赖备选模板 `assets/template.html` 的 helpers 为字符串拼接版,签名相同,组装用 `join('')` 而非 `appendChild`)。

## 模板已内置(勿重复实现)

- 依赖加载:`loadScript(srcs, timeout)` — 多 CDN 依次尝试 + 超时,失败返回 false 走降级
- 手绘 helpers(rough 缺失时自动退化为干净几何):
  - `nodeBox({ id, x, y, w, h, label, sub, color })` → `<g class="node">`(含 hachure 阴影)
  - `edgeLine({ id, x1, y1, x2, y2, label, curve, color })` → 手绘箭头(主笔画 + 两撇),`curve` 沿法线弯曲;理想路径存在 `g.dataset.d`
  - `groupArea({ x, y, w, h, label, color })` → 虚线分组框
  - `sketchRect` / `sketchPath` / `svgEl` / `text` / `hashId`(确定性 seed)/ `byId`
- 流动粒子:`flowDots(d, { color, dur, count, r })` 沿路径循环的小圆点;`syncFlows(step)` 在活跃边上重建(goStep 已自动调用)
- 交互骨架:`applyClasses` / `renderPanel`(支持 `step.kv`)/ `goStep`(含连线 draw-on 重放 + 流动粒子同步)/ stepper 事件委托 / ←→ 键盘
- 入场:`cssIntro`(draw-on + 文本 fade)、`finishIntro`(入场结束后启动流动粒子)
- 配置:`SKETCH = { seed, roughness, bowing }`

## 步骤数据结构

```js
{ label: '① 查询', title: '…', desc: '…',
  nodes: ['app', 'dns'],          // 高亮节点 id
  edges: ['q'],                   // 高亮连线 id
  kv: [['enhanced-mode', 'fake-ip']] }  // 可选,面板键值对
```

每步需要**不同子图**时,给 step 挂 `render` 函数并在 `goStep` 里调用 `step.render()` 重建 SVG(重建后对新元素跑一次 `cssIntro` 即获得绘制入场)。

## hover 聚焦 + 信息面板

节点数据加 `detail` 字段,事件委托:

```js
const diagram = document.getElementById('diagram');
diagram.addEventListener('mouseover', e => {
  const g = e.target.closest('.node');
  if (g) setFocus(g.dataset.id);
});
diagram.addEventListener('mouseout', e => {
  if (e.target.closest('.node')) setFocus(null);
});
function setFocus(id) {
  document.querySelectorAll('.node').forEach(el =>
    el.classList.toggle('is-dimmed', id !== null && el.dataset.id !== id));
  const n = id && byId(id);
  document.getElementById('info-panel').innerHTML = n
    ? `<div class="panel-swap"><h3>${n.label}</h3><p>${n.detail}</p></div>`
    : '<p>悬停节点查看详情</p>';
}
```

## 时序图

CSS 补充 `.lifeline { stroke: var(--line); stroke-dasharray: 2 5; }`:

```js
function sequenceDiagram({ actors, messages, colW = 210, top = 66, rowH = 46, margin = 24 }) {
  const w = margin * 2 + NODE_W + colW * (actors.length - 1);
  const h = top + rowH * (messages.length + 1);
  const svg = svgEl('svg', { viewBox: `0 0 ${w} ${h}`, role: 'img' });
  if (hasRough) rcHolder = rough.svg(svg);
  const colX = i => margin + NODE_W / 2 + colW * i;
  const col = id => actors.findIndex(a => a.id === id);
  actors.forEach((a, i) => {
    svg.appendChild(svgEl('line', { class: 'lifeline', x1: colX(i), y1: 56, x2: colX(i), y2: h - 8 }));
    svg.appendChild(nodeBox({ id: a.id, x: colX(i) - NODE_W / 2, y: 8, h: 40, label: a.label, color: a.color }));
  });
  messages.forEach((m, r) => {
    const i = col(m.from), j = col(m.to), y = top + rowH * (r + 1), dir = j > i ? 1 : -1;
    svg.appendChild(edgeLine({ id: m.id || `m${r}`, x1: colX(i) + 5 * dir, y1: y, x2: colX(j) - 7 * dir, y2: y, label: m.label }));
  });
  return svg;
}
```

## 状态机图

状态节点用 `nodeBox`,双向转换用 `edgeLine` 的 `curve`(往返各 -24 自然分开),边 `label` 写触发条件。自环:

```js
function selfLoop({ id, x, y, label }) { // x,y 为节点右边缘中点
  const g = svgEl('g', { class: 'edge', 'data-id': id });
  g.appendChild(sketchPath(`M ${x} ${y - 8} C ${x + 46} ${y - 28}, ${x + 46} ${y + 28}, ${x} ${y + 8}`, { seed: hashId(id) }));
  if (label) g.appendChild(text(x + 42, y - 24, label, 'edge-label'));
  return g;
}
```

## 过程演示动画

原理的动态推演。统一机制:**唯一状态变量(步骤/位置索引)单向派生一切视觉;JS 只改 class / transform / innerHTML,插值全部交给 CSS transition**——headless、后台标签页照样到达终态。`prefers-reduced-motion` 下跳过播放,直接呈现完整终态。三种通用插值原语,可自由组合:

**位移插值** — 移动元素(窗口、游标、指针)画在基准位置,状态变化只写 `transform`:

```css
.mover { transition: transform 0.45s var(--ease); }
```
```js
function applyState(p) {          // 状态 → 视觉,单向派生
  mover.style.transform = `translate(${dx(p)}px, ${dy(p)}px)`;
  items.forEach(el => el.classList.toggle('is-covered', covers(p, el)));
  renderPanel(p);                 // 面板同步解释当前状态
}
```

**形变插值** — 连续几何变换(旋转/缩放/剪切/任意矩阵)作用于一个组,transition 补间两个变换间的连续形变:

```css
.xf { transition: transform 0.8s var(--ease); transform-origin: 0 0; }  /* SVG 内 origin 必须显式声明 */
```

- 需要数学坐标(y 向上)时,外包一层 `translate(cx cy) scale(1 -1)` 翻转组,`.xf` 内直接写数学矩阵 `matrix(a, b, c, d, 0, 0)`
- 文字标签**不能放进变换组**(会镜像、形变),放屏幕坐标系由 JS 按变换结果摆位,同样加 transition 即可跟随

**逐项揭示** — 结果随进度逐个浮现:元素初始 `opacity: 0` + transition,按 `idx <= state` toggle `.is-done`,`idx === state` toggle `.is-cur`。

**自动播放驱动**:

```js
let timer = null;
function play()  { if (REDUCED) return; timer = setInterval(() => go(state.pos + 1), 1300); }
function pause() { clearInterval(timer); timer = null; }
```

节奏 1.2–1.5s/步(读者要看清内容);必须提供暂停与手动步进,手动步进时自动暂停;`setInterval` 只推进状态,单步视觉仍由 CSS 完成,符合「CSS 保底终态」;REDUCED 分支直接 `go(TOTAL - 1)` 展示完整结果。

**适用判断**:有**时间/空间推演过程**的原理才做过程动画;静态结构关系(架构、分层、依赖)用 draw-on 入场 + 步骤聚焦已足够,不要强加。

## 自动分层布局(不用力导向图)

讲解型图示要**确定性布局**,力导向每次刷新不同,禁用。分层结构:

```js
// layers: [['client'], ['gateway'], ['svc-a', 'svc-b', 'svc-c'], ['db', 'cache']]
function layoutLayers(layers, { width = 900, rowH = 100, top = 32 } = {}) {
  const pos = {};
  layers.forEach((row, li) => {
    const slot = width / row.length;
    row.forEach((id, i) => { pos[id] = { x: slot * i + (slot - NODE_W) / 2, y: top + li * rowH }; });
  });
  return pos;
}
// 用法:const pos = layoutLayers(layers); nodes.forEach(n => Object.assign(n, pos[n.id]));
```

## GSAP 编排(进阶可选,默认不用)

CSS 已覆盖全部内置动效。仅当需要**时间线级编排**(自动播放讲解、滚动驱动、精确交错序列)时引入:

```js
const hasGsap = await loadScript([
  'https://cdn.jsdelivr.net/npm/gsap@3.13.0/dist/gsap.min.js',
  'https://unpkg.com/gsap@3.13.0/dist/gsap.min.js',
]);
```

**必须遵守的教训**(实测得出):headless 截图、后台标签页等环境会冻结 rAF,GSAP 时间线会卡在中间态;`fromTo` 会立即写入起始值(如 opacity 0),冻结时元素永久不可见。因此:

1. **GSAP 只做增量修饰**:动画终态必须与「无 GSAP 时的 CSS class 状态」一致,失败仅损失过程不损失结果;
2. 禁止用 GSAP 隐藏承载信息的元素作为动画起点;
3. 自动播放用 `gsap.timeline({ repeat: -1 })` 驱动 `goStep` 序列即可,单步视觉仍由 CSS 完成。

## 大图与性能

- SVG 一次性构建;交互只 toggle class / 改 transform,禁止 JS 逐帧改样式
- 节点 >40:hachure 阴影可去掉;密集数值网格内部格子用干净 `rect`(rough 逐格画会糊且 DOM 爆炸),rough 只画整块外框
- draw-on stagger 总时长控制 ≤2s:元素多时把 15ms 间隔降到 8ms
- 单文件体积(纯文本)控制在 ~150KB 内,不内嵌 base64 图片

## 验证命令速查

```bash
# 联网观感(动画终态)
google-chrome --headless --disable-gpu --window-size=1240,900 \
  --screenshot=out.png --virtual-time-budget=15000 "file://<绝对路径>"
# 结构确定性(跳过动画,任何模式 100% 稳定)
…追加 --force-prefers-reduced-motion
# 断网降级(必须与 reduced-motion 同用,否则虚拟时钟偶发伪影)
…追加 --host-resolver-rules="MAP * ~NOTFOUND"
```
