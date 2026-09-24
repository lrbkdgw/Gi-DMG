# Gi DMG

Gi DMG v2.1.9 的原生桌面迁移版。程序使用 Python Tk 原生控件实现，**不包含 HTML、浏览器控件或 WebView**。

## 构建单 EXE（Windows）

```powershell
cd native_app
.\build_windows.ps1
```

生成物为 `exe_bin/Gi DMG v2.1.9.exe`。运行时会在 EXE 同目录创建 `date/`，每个配置是一个 JSON 文件；因此升级 EXE 不会覆盖用户配置。

## 功能

- 配置管理：新建、打开、导入、删除，自动保存到 `date/`
- 原生角色面板、技能倍率、段数、反应与伤害计算
- 武器库、圣遗物库 JSON 导入/导出
- 快速拉表与 CSV 导出
- 公式总览、设置、保存并退出/不保存并退出

`user_upload/Gi DMG v2.1.9.html` 保留为迁移参考；`native_app/main.py` 是独立原生实现，不会读取或加载该 HTML。
