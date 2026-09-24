# Gi DMG

Gi DMG 是原神伤害计算器。本次迁移新增了 `native/` 原生 Windows 实现：使用 Win32/GDI 和 C++17 重新实现窗口、输入控件、配置管理与计算引擎，不加载 HTML、不启动 WebView、不依赖网络资源。

## 原生 EXE

- 构建入口：`native/build.ps1`
- 源码：`native/src/GiDMG.cpp`、`native/src/model.cpp`
- 目标文件：`exe_bin/Gi DMG v2.2.0.exe`
- 配置目录：EXE 同目录下的 `date/`

首次启动会进入配置管理界面，可选择已有配置或新建带胡桃示例的配置。配置包括魔物等级/抗性、角色面板、技能倍率、反应、时间轴开关、历史摘要，并以 JSON 自动保存。原来的 `user_upload/Gi DMG v2.1.9.html` 仍作为 HTML 版本参考，不会被 EXE 运行时打包或套壳调用。

在 Windows 10/11 + Visual Studio 2022 中运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\native\build.ps1
```
