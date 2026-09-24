$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$out = Join-Path $root 'exe_bin\Gi DMG v3.0.0.exe'
$clang = Join-Path $root 'third_party\bin\x86_64-w64-mingw32-clang++.exe'
if (!(Test-Path $clang)) { $clang = 'x86_64-w64-mingw32-g++' }
& $clang -std=c++17 -O2 -s -municode -mwindows -static "$PSScriptRoot\main.cpp" -o $out -lcomctl32 -lcomdlg32 -lshell32 -lgdi32
Write-Host "Built: $out"
