# ChangeLog

## 2.1.9-native（2026-09-24）

- 完成 HTML 到单 EXE 的原生 GUI 重做：使用 Python Tk 原生控件，不再套壳 HTML/WebView。
- 保留配置管理、角色与技能编辑、反应伤害计算、武器库、圣遗物库、快速拉表、公式与设置等工作流。
- 增加同目录 `date/` JSON 配置持久化，支持配置导入/导出及 CSV 拉表。
- 增加 Windows PyInstaller 构建脚本与 spec，生成 `Gi DMG v2.1.9.exe`。
