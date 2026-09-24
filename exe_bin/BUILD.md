# 如何得到这里的 `Gi DMG [ver.].exe`

单文件 EXE 必须在 **Windows** 上打包（PyInstaller 不支持交叉编译），两种方式任选：

## 1. 本地一键构建

```bat
cd exe_src
build.bat
```

脚本会自动创建虚拟环境、安装 `requirements.txt`、运行测试，再用 PyInstaller 打包，
最后把产物复制到本目录，文件名形如 `Gi DMG v2.1.9.exe`。

## 2. GitHub Actions

仓库内的工作流 **构建单文件 EXE**（`.github/workflows/build-exe.yml`）在 `windows-latest` 上执行同样的流程：

- 任何改动 `exe_src/**` 的推送或 PR 都会自动构建，产物作为 Artifact 下载；
- 手动触发（workflow_dispatch）时勾选 `commit_binary`，会把构建好的 EXE 直接提交回本目录；
- 或者在提交信息里带上 `[commit-exe]`，推送后工作流同样会把 EXE 提交回本目录。

> 本目录只存放构建产物，源码在 `exe_src/`。
