这是放置单 EXE 形式的结果的文件夹。

文件名格式为 `Gi DMG [ver.].exe`。

构建入口：`native_app/build_windows.ps1`。生成的 EXE 为 Tk 原生 GUI，未打包 HTML/WebView；由于当前构建环境为 Linux，Windows 二进制需在 Windows 上执行脚本生成。