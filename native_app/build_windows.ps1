$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
python -m pip install --upgrade pyinstaller
python -m PyInstaller --clean --noconfirm Gi_DMG.spec
New-Item -ItemType Directory -Force ..\exe_bin | Out-Null
Copy-Item 'dist\Gi DMG v2.1.9.exe' '..\exe_bin\Gi DMG v2.1.9.exe' -Force
Write-Host 'Built exe_bin\Gi DMG v2.1.9.exe'
