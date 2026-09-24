@echo off
rem Windows 一键打包：创建/复用 .venv，装依赖，跑测试，输出 ..\exe_bin\Gi DMG v*.exe
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [build] 创建虚拟环境 .venv ...
  py -3 -m venv .venv || python -m venv .venv || goto :fail
)

echo [build] 安装依赖 ...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :fail

echo [build] 开始打包 ...
".venv\Scripts\python.exe" build.py %* || goto :fail

echo [build] 全部完成。
exit /b 0

:fail
echo [build] 失败，请查看上面的输出。
exit /b 1
