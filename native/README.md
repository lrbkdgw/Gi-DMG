# Gi DMG Native

这是 Gi DMG 的 Windows 原生版本。它不是 HTML、Electron、WebView 或浏览器壳：窗口、布局、输入框、时间轴摘要和计算引擎均由 Win32 + GDI 绘制/创建，计算逻辑在 `src/model.cpp` 中独立实现。

## 构建

在 Windows 10/11 的 **x64 Native Tools Command Prompt for VS 2022** 中运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\native\build.ps1
```

脚本优先使用 CMake + Visual Studio 2022，找不到 CMake 时回退到 `cl.exe`。发布构建使用静态 CRT，输出为单文件：

```text
exe_bin/Gi DMG v2.2.0.exe
```

EXE 不依赖项目中的 HTML、CDN、字体、DLL 或运行时服务器。运行时只会在 EXE 同级创建/读写 `date/` 配置目录。

## 原生实现范围

- 配置管理首屏：新建、打开、删除、刷新；配置保存在 `date/*.json`。
- 左侧角色/魔物/时间轴/历史导航，中央角色编辑区，右侧即时伤害统计。
- 角色、武器攻击、生命、暴击、元素精通、技能倍率、命中次数、元素抗性等输入。
- 直伤、蒸发/融化、超激化/蔓激化和绽放系反应的原生计算，以及防御区/抗性区。
- 顶部“灵动岛”式原生操作条：保存并退出、不保存、快速拉表、设置。
- JSON 导入/导出、公式说明、面板明细、角色伤害占比、基准/历史摘要。

导入的配置是数据格式而不是页面资源；即使删除原始 HTML，EXE 仍可独立运行。
