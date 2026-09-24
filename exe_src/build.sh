#!/usr/bin/env bash
# Linux / macOS 一键构建（产物仅供本地自测，正式 EXE 需要在 Windows 上打包）
set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"
if [ ! -x ".venv/bin/python" ]; then
  echo "[build] 创建虚拟环境 .venv ..."
  "$PY" -m venv .venv
fi

echo "[build] 安装依赖 ..."
.venv/bin/python -m pip install --upgrade pip >/dev/null
.venv/bin/python -m pip install -r requirements.txt

echo "[build] 开始打包 ..."
.venv/bin/python build.py "$@"
