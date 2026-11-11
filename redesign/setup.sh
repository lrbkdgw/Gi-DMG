#!/usr/bin/env bash
# 重建 /tmp 下的一次性工具链（无头 Chromium + 中文字体 + Tailwind）。沙箱重置后执行：bash redesign/setup.sh
set -e
mkdir -p /tmp/tools /tmp/tw /tmp/al2023 /tmp/fonts/noto
cd /tmp/tools
[ -d node_modules/puppeteer-core ] || { npm init -y >/dev/null 2>&1; npm i @sparticuz/chromium@153.0.0 puppeteer-core @expo-google-fonts/noto-sans-sc acorn >/dev/null 2>&1; }
[ -d /tmp/al2023/lib ] || node -e "require('fs').writeFileSync('/tmp/al2023.tar',require('zlib').brotliDecompressSync(require('fs').readFileSync('/tmp/tools/node_modules/@sparticuz/chromium/bin/al2023.tar.br')))" && tar -xf /tmp/al2023.tar -C /tmp/al2023 2>/dev/null || true
# @sparticuz/chromium 只在 /tmp/fonts 不存在时才解包自带的 fonts.conf，这里手动解到 /tmp/fonts
[ -f /tmp/fonts/fonts.conf ] || { node -e "require('fs').writeFileSync('/tmp/fonts.tar',require('zlib').brotliDecompressSync(require('fs').readFileSync('/tmp/tools/node_modules/@sparticuz/chromium/bin/fonts.tar.br')))" && tar -xf /tmp/fonts.tar -C /tmp/fonts; }
for w in 400Regular 500Medium 600SemiBold 700Bold; do cp -n node_modules/@expo-google-fonts/noto-sans-sc/$w/*.ttf /tmp/fonts/noto/ 2>/dev/null || true; done
cat > /tmp/tools/env.sh <<'EOS'
export LD_LIBRARY_PATH=/tmp/al2023/lib
export FONTCONFIG_PATH=/tmp/fonts
export HOME=/home/user
EOS
cd /tmp/tw
[ -d node_modules/tailwindcss ] || { npm init -y >/dev/null 2>&1; npm i tailwindcss@3.4.17 >/dev/null 2>&1; }
echo "tools ready"
