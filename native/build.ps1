$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$build = Join-Path $PSScriptRoot 'build'

if (Get-Command cmake -ErrorAction SilentlyContinue) {
    cmake -S $PSScriptRoot -B $build -G 'Visual Studio 17 2022' -A x64
    cmake --build $build --config Release --parallel
} elseif (Get-Command cl.exe -ErrorAction SilentlyContinue) {
    New-Item -ItemType Directory -Force $build | Out-Null
    cl.exe /nologo /std:c++17 /O2 /W4 /EHsc /utf-8 /DUNICODE /D_UNICODE /DWIN32_LEAN_AND_MEAN /DNOMINMAX /MT /Fe:"$build\Gi DMG v2.2.0.exe" "$PSScriptRoot\src\GiDMG.cpp" "$PSScriptRoot\src\model.cpp" user32.lib gdi32.lib comctl32.lib comdlg32.lib shell32.lib /link /SUBSYSTEM:WINDOWS
} else {
    throw '需要 Visual Studio 2022（cl.exe）或 CMake。'
}

$exe = Get-ChildItem -Path $build -Filter 'Gi DMG v2.2.0.exe' -Recurse | Select-Object -First 1
if (-not $exe) { throw '编译结束但没有找到 EXE。' }
$destination = Join-Path $root 'exe_bin\Gi DMG v2.2.0.exe'
New-Item -ItemType Directory -Force (Split-Path $destination) | Out-Null
Copy-Item $exe.FullName $destination -Force
Write-Host "已生成：$destination"
