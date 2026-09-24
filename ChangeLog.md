## v2.2.0 · 原生单 EXE 迁移

- 基于原有 v2.1.9 HTML 的功能模型，新增独立的 C++17/Win32 原生 Windows 实现；EXE 不加载 HTML、WebView、Electron、CDN 或外部 DLL。
- 新增配置管理首屏：可新建、打开、删除、刷新配置，配置自动保存到 EXE 同级 `date/` 目录。
- 重做三栏工作区：左侧角色导航与功能导航、中央编辑工作区、右侧基准/伤害统计，并加入顶部原生“灵动岛”操作条。
- 原生实现面板属性、技能倍率、元素反应、防御区、抗性区、时间轴 DPS、面板明细、角色伤害占比、JSON 导入/导出与历史摘要。
- 增加 `native/CMakeLists.txt` 与 `native/build.ps1`，Release 使用静态 CRT，发布结果为单文件 `exe_bin/Gi DMG v2.2.0.exe`。
