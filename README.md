# Gi DMG

原神伤害计算器。项目包含原始单 HTML 版本，以及完全独立重写的 Windows 原生 GUI 版本。

## 原生 EXE

原生版本位于 `native/main.cpp`，直接使用 Win32/GDI 控件绘制，不包含 Chromium、WebView、Electron、HTML、CSS 或 JavaScript 运行时。

主要功能：

- 魔物等级及元素抗性配置
- 角色基础面板、武器、暴击与技能倍率配置
- 循环时间轴及 DPS 展示
- 原生伤害计算（攻击区、倍率区、增伤区、防御区、抗性区、期望暴击）
- 启动配置管理，以及程序同目录 `date` 文件夹自动持久化
- 顶部“灵动岛”配置菜单：保存、保存并退出、不保存并退出、快速拉表、设置
- 单文件 Windows EXE，无需安装

## 构建

在带有 MinGW-w64 的 Windows PowerShell 中执行：

```powershell
./native/build.ps1
```

也可直接使用：

```text
x86_64-w64-mingw32-g++ -std=c++17 -O2 -s -municode -mwindows -static native/main.cpp -o "exe_bin/Gi DMG v3.0.0.exe" -lcomctl32 -lcomdlg32 -lshell32 -lgdi32
```

## 数据

每个配置保存为 EXE 同目录下 `date/<配置名>.gidmg`。数据为本地文件，不访问网络。
