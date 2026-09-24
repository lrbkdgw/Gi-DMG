"""一条命令打出单文件 EXE。

用法（Windows，建议在虚拟环境里）：
    python build.py                 # 打包并输出到 ../exe_bin/Gi DMG v2.1.9.exe
    python build.py --no-clean      # 保留 build/ 中间产物
    python build.py --console       # 保留控制台窗口（排查启动问题用）
    python build.py --output DIR    # 自定义输出目录

脚本做的事：
    1. 检查依赖（PySide6 / PyInstaller）；
    2. 跑一遍单元测试（可用 --skip-tests 跳过）；
    3. 调用 PyInstaller，把 gidmg/assets 一并塞进单文件；
    4. 把产物重命名成仓库约定的 `Gi DMG [ver.].exe` 放到 /exe_bin。

在 Linux / macOS 上同样可以运行，只是产物不是 .exe，仅供本地自测。
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

from gidmg.version import VERSION  # noqa: E402

APP_NAME = f"Gi DMG v{VERSION}"        # 最终交付的文件名（仓库约定）
BUILD_NAME = "GiDMG"                   # PyInstaller 内部用名，避免空格/小数点带来的边角问题
ENTRY = HERE / "main.py"
ASSETS = HERE / "gidmg" / "assets"


def log(msg: str) -> None:
    print(f"[build] {msg}", flush=True)


def ensure_deps() -> None:
    missing = []
    for mod, pkg in (("PySide6", "PySide6"), ("PyInstaller", "pyinstaller")):
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        log(f"缺少依赖：{', '.join(missing)}")
        log(f"请先执行：{sys.executable} -m pip install -r requirements.txt")
        raise SystemExit(1)


def run_tests() -> None:
    log("运行单元测试……")
    proc = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q"], cwd=HERE)
    if proc.returncode != 0:
        log("测试未通过，已中止打包（可用 --skip-tests 跳过）。")
        raise SystemExit(proc.returncode)


def _pyinstaller_cmd(args: argparse.Namespace, dist: Path, work: Path,
                     with_icon: bool) -> list:
    sep = ";" if os.name == "nt" else ":"
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--name", BUILD_NAME,
        "--distpath", str(dist),
        "--workpath", str(work),
        "--specpath", str(work),
        "--add-data", f"{ASSETS}{sep}gidmg/assets",
        # 只保留真正用到的 Qt 模块，避免单文件膨胀
        "--exclude-module", "PySide6.QtWebEngineCore",
        "--exclude-module", "PySide6.QtWebEngineWidgets",
        "--exclude-module", "PySide6.QtQuick",
        "--exclude-module", "PySide6.QtQml",
        "--exclude-module", "PySide6.Qt3DCore",
        "--exclude-module", "PySide6.QtMultimedia",
        "--exclude-module", "PySide6.QtCharts",
        "--exclude-module", "PySide6.QtDataVisualization",
        "--exclude-module", "PySide6.QtNetworkAuth",
        "--exclude-module", "PySide6.QtPdf",
        "--exclude-module", "tkinter",
        "--exclude-module", "unittest",
        "--exclude-module", "pytest",
    ]
    if not args.console:
        cmd.append("--windowed")
    icon = HERE / "gidmg" / "assets" / "app.ico"
    if with_icon and icon.exists():
        cmd += ["--icon", str(icon)]
    cmd.append(str(ENTRY))
    return cmd


def build(args: argparse.Namespace) -> Path:
    work = HERE / "build"
    dist = HERE / "dist"
    if args.clean:
        for d in (work, dist):
            shutil.rmtree(d, ignore_errors=True)

    log("调用 PyInstaller……")
    cmd = _pyinstaller_cmd(args, dist, work, with_icon=True)
    log(" ".join(f'"{c}"' if " " in c else c for c in cmd))
    proc = subprocess.run(cmd, cwd=HERE)
    if proc.returncode != 0:
        # 少数环境下嵌入图标会失败（图标资源写入依赖额外组件），退回无图标再来一次
        log("打包失败，去掉图标重试一次……")
        shutil.rmtree(work, ignore_errors=True)
        cmd = _pyinstaller_cmd(args, dist, work, with_icon=False)
        log(" ".join(f'"{c}"' if " " in c else c for c in cmd))
        proc = subprocess.run(cmd, cwd=HERE)
        if proc.returncode != 0:
            raise SystemExit(proc.returncode)

    suffix = ".exe" if os.name == "nt" else ""
    produced = dist / f"{BUILD_NAME}{suffix}"
    if not produced.exists():  # PyInstaller 在个别平台上不带后缀
        alt = dist / BUILD_NAME
        produced = alt if alt.exists() else produced
    if not produced.exists():
        log(f"没有找到产物：{produced}")
        log(f"dist 目录内容：{[p.name for p in dist.glob('*')] if dist.exists() else '不存在'}")
        raise SystemExit(1)

    out_dir = Path(args.output) if args.output else (REPO / "exe_bin")
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{APP_NAME}{suffix}"
    shutil.copy2(produced, target)
    size = target.stat().st_size / (1024 * 1024)
    log(f"完成：{target}（{size:.1f} MB）")

    if args.clean:
        shutil.rmtree(work, ignore_errors=True)
    return target


def main() -> int:
    ap = argparse.ArgumentParser(description="打包 Gi DMG 单文件 EXE")
    ap.add_argument("--output", help="输出目录，默认 ../exe_bin")
    ap.add_argument("--console", action="store_true", help="保留控制台窗口")
    ap.add_argument("--skip-tests", action="store_true", help="跳过单元测试")
    ap.add_argument("--no-clean", dest="clean", action="store_false", help="保留中间产物")
    ap.set_defaults(clean=True)
    args = ap.parse_args()

    log(f"版本：{VERSION}　Python：{sys.version.split()[0]}　平台：{sys.platform}")
    ensure_deps()
    if not args.skip_tests:
        run_tests()
    build(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
