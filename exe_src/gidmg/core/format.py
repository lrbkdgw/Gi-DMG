"""数字/文本格式化，保持与 HTML 版一致的显示效果。"""

from __future__ import annotations

import datetime as _dt
import math
from typing import Any

from .engine import jround


def js_num(value: Any) -> str:
    """模拟 JS 模板字符串里的数字转文本：2 → "2"，1.5 → "1.5"。"""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isnan(f):
        return "NaN"
    if math.isinf(f):
        return "Infinity" if f > 0 else "-Infinity"
    if f == int(f) and abs(f) < 1e16:
        return str(int(f))
    return repr(f)


def thousands(value: Any) -> str:
    """等价 JS 的 Number.toLocaleString()（整数千分位）。"""
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"


def rounded(value: Any) -> str:
    """等价 Math.round(x).toLocaleString()，全站最常用的数值展示。"""
    try:
        return f"{jround(float(value or 0)):,}"
    except (TypeError, ValueError):
        return "0"


def dps(value: Any) -> str:
    return rounded(value) + "/s"


def pct(value: Any, digits: int = 1) -> str:
    try:
        return f"{float(value or 0):.{digits}f}%"
    except (TypeError, ValueError):
        return "0.0%"


def signed(value: Any, digits: int = 1) -> str:
    try:
        f = float(value or 0)
    except (TypeError, ValueError):
        f = 0.0
    txt = f"{f:.{digits}f}".rstrip("0").rstrip(".") or "0"
    return ("+" + txt) if f >= 0 else txt


def trim(value: Any, digits: int = 2) -> str:
    """去掉末尾多余的 0：12.50 → "12.5"，12.00 → "12"。"""
    try:
        f = float(value or 0)
    except (TypeError, ValueError):
        return "0"
    txt = f"{f:.{digits}f}".rstrip("0").rstrip(".")
    return txt or "0"


def hist_time(ms: Any) -> str:
    """对应 HTML 的 fmtHistTime()：今天显示时分，其余显示月日时分。"""
    try:
        t = _dt.datetime.fromtimestamp(float(ms) / 1000.0)
    except (TypeError, ValueError, OSError, OverflowError):
        return "未知时间"
    now = _dt.datetime.now()
    if t.date() == now.date():
        return f"今天 {t:%H:%M}"
    if t.date() == (now - _dt.timedelta(days=1)).date():
        return f"昨天 {t:%H:%M}"
    if t.year == now.year:
        return f"{t:%m-%d %H:%M}"
    return f"{t:%Y-%m-%d %H:%M}"


def duration(seconds: Any) -> str:
    try:
        f = float(seconds or 0)
    except (TypeError, ValueError):
        f = 0.0
    return f"{trim(f, 2)}s"
