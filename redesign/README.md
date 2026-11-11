# redesign/ —— 界面重设计的源码与验证脚本

仓库根目录的 `Gi DMG v2.2.0.html` 是由本目录生成的。本目录**不参与运行**，删掉它不影响应用。

## 先看这一条

构建脚本的输入是**提交 `2e43850` 里的原版 HTML**（`split.py` 用 `git show` 取出），不是当前的 HTML。所以：

- 重新运行 `build.py` 会覆盖根目录的 HTML，直接改在 HTML 里的内容会丢失。
- 之后如果计算逻辑有改动，这套脚本不会自动跟上。`codemod.py` 的每条替换规则都按原版脚本核对过出现次数，输入变了就会报错停下。

也就是说，它是「这次改版怎么做出来、怎么验证」的记录，不是长期的构建系统。合并后二选一：

1. 像以前一样直接维护 HTML（样式和结构在文件里都是可读的内联代码），本目录只作参考，或者直接删掉。
2. 想继续用这套流程，就把 `split.py` 里固定的提交号换成新的基线，并按报错更新 `codemod.py` 的规则。

## 文件

| 路径 | 作用 |
| --- | --- |
| `src/app.css` | 设计系统：变量、浅色/深色主题、全部组件样式、响应式规则 |
| `src/body.html` | 静态页面结构（保留原版全部元素 ID，新增 `btnTheme`） |
| `src/codemod.py` | 只改写主脚本里与展示有关的部分：模板里的类名与结构、图表配色 |
| `split.py` | 把原版 HTML 按区块拆到 `/tmp/gi-orig` |
| `build.py` | 组装并自检（标签配对、原版元素 ID 齐全且无重复、不含 Google Fonts 与 Cloudflare 引用），写回根目录的 HTML |
| `setup.sh` | 在 `/tmp` 下安装工具：Tailwind 3.4.17，以及验证用的无头 Chromium 和中文字体 |
| `qa/` | 验证脚本，见下 |

## 构建

```bash
bash redesign/setup.sh      # 只需一次，需要能访问 npm
python3 redesign/build.py   # 约 2 秒；GI_TARGET=路径 可改输出位置
```

## 验证

```bash
source /tmp/tools/env.sh
node --test timeline.test.cjs        # 仓库原有的 18 项测试
node redesign/qa/parity.mjs          # 同一套 1087 步操作在原版与新版上逐步对比状态和结果，约 150 秒
node redesign/qa/interact.mjs        # 真实键鼠输入、导出/导入往返、拉表模式下的入口显隐，与原版对照
node redesign/qa/shots_all.mjs "Gi DMG v2.2.0.html" /tmp/shots/x - 1440 900   # 35 步界面走查，每步附带版面体检
node redesign/qa/ast_diff.mjs /tmp/gi-orig/10_main.js /tmp/gi-gen/main.js     # 主脚本的结构差异（忽略字符串内容）
```

`shots_all.mjs` 的第三个参数填 `dark` 走深色主题，后两个参数是视口宽高。版面体检会报告：页面横向溢出、越出视口的元素、被静默裁切的内容、越出视口的弹窗。`slices.mjs` 和 `sheet.mjs` 用来给单列布局切长图、把多张截图拼成一张便于目检。

验证脚本是按 Linux 环境写的（`setup.sh` 装的是 Linux 版无头 Chromium）。在别的系统上跑，需要把 `qa/lib.mjs` 里的浏览器路径换成本机的 Chrome。
