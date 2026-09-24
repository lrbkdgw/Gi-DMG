# Gi DMG · 原神伤害计算器

一个面向循环轴（rotation）的原神期望伤害计算器，提供两种形态：

| 形态 | 位置 | 说明 |
| --- | --- | --- |
| 单文件 HTML | `html_bin/Gi DMG v2.1.9.html` | 双击即用，浏览器打开，无需安装 |
| 单文件 EXE | `exe_bin/Gi DMG v2.1.9.exe` | Windows 原生桌面程序，配置自动落盘 |

两者**计算结果完全一致**：EXE 不是把网页套壳，而是用 Python + PySide6（Qt Widgets）重写的原生程序，
计算引擎逐字段对拍 HTML 版实现（见下文「测试」）。

---

## 一、功能总览

- **多角色队伍**：每个角色维护基础/武器/固定面板、暴击、元素伤害加成，可单独启用或停用。
- **伤害来源**：普通伤害、剧变反应、特殊直伤（月曜 / 星超导 / 星扩散）、特殊反应（多角色贡献加权）。
- **天赋与效果**：面板属性、伤害类型加成、元素伤害加成、敌人减抗/减防、反应加成、月曜/星烁分区、羽毛附加伤害；
  支持作用于自身 / 全队 / 指定角色 / 指定伤害来源。
- **循环时间轴**：为每个来源设置出伤时刻与持续时间，支持瞬发、持续均匀·锁面板、持续均匀·随动三种出伤模式，
  按 20 段均匀采样结算 Buff 的动态变化，并给出全队 DPS。
- **元素共鸣**：按队伍元素自动判定并计入。
- **伤害占比**：环形图 + 明细条，区分角色直伤、羽毛提供伤害与反应伤害。
- **面板明细 / 时序解析**：逐角色列出各类加成来源；点击伤害统计卡片可查看该来源在持续期间的面板分段。
- **基准对比**：把当前结果存为基准，之后实时显示差值。
- **快捷配置助手**：按突破/武器/圣遗物副词条推算面板，一键覆盖角色面板；武器与圣遗物可存入本地库复用。
- **快速拉表**：给角色保存多套「方案 + 代价」，枚举所有组合批量结算，支持排序、剔除被偏序方案、导出 CSV / Markdown。
- **计算公式总览**：列出各区乘算关系与等级系数表（EXE 版在配置管理界面的 Σ 按钮）。

## 二、EXE 与 HTML 的差异

计算逻辑完全相同，界面基本一致，差异集中在「配置怎么存、怎么进」这件事上（详见 `user_upload/What_Change.md`）：

1. **自动落盘**：全局设置、武器库、圣遗物库、每份配置都自动保存在 EXE 同目录的 `date/` 文件夹里，不再依赖浏览器存储。
2. **配置管理界面**：启动后先进入配置管理页，可以打开已有配置、新建空白配置或从示例模板开始；
   「计算公式」按钮也移到了这一页。
3. **灵动岛**：进入配置后，窗口顶部中央是一个显示当前配置名的胶囊；点击后展开成四个按钮
   —— 保存并退出 / 不保存并退出 / 快速拉表 / 设置。它平时缩在窗口顶边，鼠标靠近时自动弹出。
4. **顶部四个按钮已移除**：原网页右上角的四个按钮统一收进灵动岛与配置管理页。

数据目录结构：

```
Gi DMG v2.1.9.exe
date/
├── configs/                  # 每份配置一个 JSON
├── drafts/                   # 未保存的编辑草稿（崩溃后可恢复）
├── library/
│   ├── weapons.json          # 武器库
│   └── artifacts.json        # 圣遗物库
├── history/
│   ├── config_history.json   # 配置历史
│   └── quicktable_history.json  # 拉表结果历史
└── app_settings.json         # 全局设置
```

> 配置的编辑在「保存并退出」时才落盘；全局设置、武器库、圣遗物库改完立即保存。
> 编辑过程中会定期写 `drafts/`，异常退出后下次打开该配置会询问是否恢复。

## 三、使用方式

### HTML 版

直接双击 `html_bin/Gi DMG v2.1.9.html`。

### EXE 版

下载 `exe_bin/Gi DMG v2.1.9.exe` 双击运行；首次运行会在同目录创建 `date/` 文件夹。
建议放在一个可写目录（不要直接放在 `C:\Program Files` 下）。

常用快捷键：`Ctrl+S` 保存、`Ctrl+Q` 保存并退出、`Ctrl+,` 全局设置、`Esc` 收起灵动岛。

## 四、从源码运行与打包

源码在 `exe_src/`：

```
exe_src/
├── main.py                 # 入口
├── build.py / build.bat / build.sh
├── requirements.txt
├── gidmg/
│   ├── core/               # 纯计算层：constants / state / engine / quickset / quicktable / storage / format
│   ├── ui/                 # 界面层：theme / widgets / launcher / island / editor / panels_* / dialogs/*
│   └── assets/             # 图标（Lucide v0.468.0，ISC）与八元素图形
├── tests/                  # 与 HTML 版的对拍测试
└── tools/dev_preview.py    # 无显示器环境下渲染界面截图，便于排版自检
```

运行：

```bash
cd exe_src
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt   # Windows: .venv\Scripts\python.exe
.venv/bin/python main.py
```

打包单文件 EXE（**必须在 Windows 上执行**，PyInstaller 不支持交叉编译）：

```bat
cd exe_src
build.bat
```

`build.bat` 会自动建虚拟环境、装依赖、跑测试、调用 PyInstaller，并把产物放到 `exe_bin\Gi DMG v2.1.9.exe`。
Linux / macOS 上可以用 `./build.sh` 打本地自测包（产物不是 .exe）。

也可以直接用 GitHub Actions：仓库里的 **构建单文件 EXE** 工作流（`.github/workflows/build-exe.yml`）在
`windows-latest` 上完成同样的流程，产物作为 Artifact 上传；手动触发（workflow_dispatch）时可勾选
`commit_binary`，让它把 EXE 提交回 `exe_bin/`。

## 五、测试

```bash
cd exe_src
.venv/bin/python -m pytest tests -q
```

测试会从 `html_bin/Gi DMG v2.1.9.html` 里抽出网页版的脚本，在 Node 上跑同一批随机配置，
再和 Python 引擎逐字段比对（总伤害、DPS、每个来源的期望/暴击/非暴击、面板、伤害占比、
快捷配置助手推算出的面板等），任何公式偏差都会让测试失败。没有安装 Node 时对拍用例会自动跳过。

## 六、许可与致谢

- 界面图标：[Lucide](https://lucide.dev) v0.468.0，ISC 协议，声明见 `exe_src/gidmg/assets/icons/NOTICE.md`。
- 元素图标：来自原项目 HTML 内置资源。
- 桌面端框架：[Qt for Python (PySide6)](https://doc.qt.io/qtforpython/)，LGPLv3。
