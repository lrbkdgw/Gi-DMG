# EXE 发布目录

原生 Windows 单文件构建入口为 `../native/build.ps1`，当前已生成：

`Gi DMG v2.2.0.exe`

该文件由 GitHub Actions 的 Windows x64 MSVC 环境编译，使用静态 CRT，PE 架构为 x86-64。EXE 不依赖 HTML、WebView、CDN 或项目运行时；运行时只会在 EXE 同级创建/读写 `date/` 配置目录。
