# Gi DMG · 原神伤害计算器

单文件 Web 应用（`Gi DMG v2.2.0.html`）：打开即用，无需构建。前端为「Atelier」设计系统——温暖纸白画布、发丝级描边、墨黑主操作与单一黄铜强调色。

## 目录结构

| 文件 | 说明 |
| --- | --- |
| `Gi DMG v2.2.0.html` | 完整应用：HTML 结构、设计系统样式、计算引擎与全部 UI 逻辑（离线可用） |
| `timeline.test.cjs` | 时间轴 / 结算引擎回归测试（Node.js 18+，无依赖） |
| `finish_date/*.json` | 示例配置，可直接在应用内「导入配置」 |

## 界面结构

```
#landing          启动页
#genshinView      应用外壳（CSS Grid：268px ／ 自适应 ／ 338px）
├─ aside.studio-left-sidebar    品牌、魔物 / 角色 / 历史 / 时间轴导航
├─ main.studio-main             工作区：角色编辑器、魔物设置、循环时间轴
└─ aside.studio-right-sidebar   工具条、基准值、伤害统计与总期望伤害
```

所有面板、弹窗与列表均由原生 DOM + 计算引擎渲染；导入／导出、快速拉表、历史记录、伤害占比等行为与 v2.2.0 保持一致。

## 设计系统

样式集中在 `<style id="gi-dmg-design-system">`，按「令牌 → 基础 → 组件 → 布局 → 弹窗 → 响应式」分层，语义类由模板统一复用（`.text-ink-2`、`.bg-subtle`、`.border-line` 等）。

| 令牌 | 值 | 用途 |
| --- | --- | --- |
| `--bg` | `#f3f3ef` | 画布 |
| `--surface` / `--surface-2` / `--surface-3` | `#ffffff` / `#f7f7f4` / `#eeeee9` | 卡片、输入、悬停 |
| `--line` / `--line-2` | `#e6e5de` / `#d6d5cc` | 发丝描边 |
| `--ink` / `--ink-2` / `--ink-3` | `#1b1b17` / `#56564e` / `#7b7b72` | 正文三级文本 |
| `--accent` / `--accent-soft` | `#8a6a3c` / `#f3ebdc` | 强调（DPS、最高 DPS、激活态） |
| `--danger` / `--info` / `--violet` / `--green` | 见样式表 | 校验、元素与分类标签 |

- 字体：`Inter`（界面）+ `Instrument Serif`（品牌字体）+ 系统中文字体回退；数字统一等宽对齐。
- 圆角：8 / 11 / 15 / 20px；控件高度 32px，密集表格内 26–28px。
- 元素色仅用于图标、结果徽章与时间轴轨道，卡片与容器保持中性。
- 无障碍：可见焦点环、对比度达标的次级文本、`prefers-reduced-motion` 降级。

## 开发

```bash
node --test timeline.test.cjs   # 运行引擎回归测试
```

浏览器直接打开 HTML 即可预览；配置、武器库与圣遗物库保存在 `localStorage`。
