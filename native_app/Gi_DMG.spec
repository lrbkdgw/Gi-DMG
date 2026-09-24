# PyInstaller spec: one Windows executable, no HTML/webview dependency.
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

a = Analysis(['main.py'], pathex=['.'], binaries=[], datas=[], hiddenimports=[],
             hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=['tkinter.test'],
             noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='Gi DMG v2.1.9',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=True,
          console=False, disable_windowed_traceback=False)
