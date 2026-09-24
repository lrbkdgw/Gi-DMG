# EXE 发布目录

原生 Windows 单文件构建入口为 `../native/build.ps1`，编译成功后会生成：

`Gi DMG v2.2.0.exe`

本 Linux 工作区无法调用 Windows MSVC，因此没有伪造不可运行的 `.exe`；请在 Windows 10/11 + Visual Studio 2022 上执行构建脚本。Release 使用静态 CRT，生成的 EXE 不依赖 HTML、WebView、CDN、DLL 或项目运行时。
