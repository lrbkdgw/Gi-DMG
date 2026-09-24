"""图标加载：Lucide 线性图标 + 八元素图标。

图标文件从 HTML 版内置的 lucide v0.468.0 与 ELEMENT_ICON_DATA 中原样导出，
因此 EXE 与网页版用的是同一套图形。SVG 里的 currentColor 在这里按需替换。
"""

from __future__ import annotations

import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from . import theme


def assets_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "gidmg" / "assets"  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent / "assets"


ICON_DIR = assets_dir() / "icons"
ELEMENT_DIR = assets_dir() / "elements"

_FALLBACK = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
    'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
    'stroke-linejoin="round"><circle cx="12" cy="12" r="9"/></svg>'
)


@lru_cache(maxsize=256)
def _svg_source(name: str) -> str:
    path = ICON_DIR / f"{name}.svg"
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return _FALLBACK


@lru_cache(maxsize=512)
def _element_source(name: str) -> Optional[str]:
    path = ELEMENT_DIR / f"{name}.svg"
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def device_ratio() -> float:
    """当前屏幕的缩放比。

    位图必须按屏幕实际像素渲染：若位图的 devicePixelRatio 与屏幕不一致，
    QIcon 会把它按逻辑尺寸直接贴图，导致图标被裁掉一角。
    """
    app = QGuiApplication.instance()
    if app is None:
        return 1.0
    screen = app.primaryScreen()
    if screen is None:
        return 1.0
    return max(1.0, float(screen.devicePixelRatio()))


def _blank(size: int, dpr: float) -> QPixmap:
    pm = QPixmap(max(1, round(size * dpr)), max(1, round(size * dpr)))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.GlobalColor.transparent)
    return pm


_FILL_STYLE_RE = re.compile(r"fill:\s*#[0-9A-Fa-f]{3,8}")
_FILL_ATTR_RE = re.compile(r'fill="#[0-9A-Fa-f]{3,8}"')
_STROKE_STYLE_RE = re.compile(r"stroke:\s*#[0-9A-Fa-f]{3,8}")


def recolor(svg: str, color: str) -> str:
    """把 SVG 里写死的颜色换成指定颜色。

    元素图标是从 HTML 版里原样导出的 Illustrator SVG，用的是 <style> 里的类
    （例如 .st1{fill:#FF6640;}），没有 currentColor，所以要连样式表一起替换。
    display:none 的图层保持原样，避免把隐藏图层显出来。
    """
    out = svg.replace("currentColor", color)
    out = _FILL_STYLE_RE.sub(f"fill:{color}", out)
    out = _FILL_ATTR_RE.sub(f'fill="{color}"', out)
    out = _STROKE_STYLE_RE.sub(f"stroke:{color}", out)
    return out


def _render(svg: str, size: int, dpr: float = 1.0) -> QPixmap:
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pm = _blank(size, dpr)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    renderer.render(p, QRectF(0, 0, size * dpr, size * dpr))
    p.end()
    return pm


@lru_cache(maxsize=2048)
def _pixmap(name: str, size: int, color: str, stroke: float, dpr: float) -> QPixmap:
    svg = _svg_source(name).replace("currentColor", color)
    if stroke != 2.0:
        svg = svg.replace('stroke-width="2"', f'stroke-width="{stroke}"')
    return _render(svg, size, dpr)


def pixmap(name: str, size: int = 16, color: str = theme.MUTED, stroke: float = 2.0) -> QPixmap:
    return _pixmap(name, size, color, stroke, device_ratio())


@lru_cache(maxsize=2048)
def _icon(name: str, size: int, color: str, disabled_color: str,
          active_color: Optional[str], stroke: float, dpr: float) -> QIcon:
    ic = QIcon()
    ic.addPixmap(pixmap(name, size, color, stroke), QIcon.Mode.Normal, QIcon.State.Off)
    ic.addPixmap(pixmap(name, size, active_color or color, stroke), QIcon.Mode.Active, QIcon.State.Off)
    ic.addPixmap(pixmap(name, size, active_color or color, stroke), QIcon.Mode.Selected, QIcon.State.Off)
    ic.addPixmap(pixmap(name, size, disabled_color, stroke), QIcon.Mode.Disabled, QIcon.State.Off)
    return ic


def icon(name: str, size: int = 16, color: str = theme.MUTED,
         disabled_color: str = "#b3bac3", active_color: Optional[str] = None,
         stroke: float = 2.0) -> QIcon:
    return _icon(name, size, color, disabled_color, active_color, stroke, device_ratio())


def blue(name: str, size: int = 16) -> QIcon:
    return icon(name, size, theme.BLUE)


def muted(name: str, size: int = 16) -> QIcon:
    return icon(name, size, theme.MUTED)


@lru_cache(maxsize=512)
def _element_pixmap(elem: str, size: int, color: Optional[str], dpr: float) -> QPixmap:
    """元素图标；没有对应 SVG 时退化成纯色圆点。"""
    src = _element_source(elem)
    tint = color or theme.element_color(elem)
    if src:
        return _render(recolor(src, tint) if color else src, size, dpr)
    pm = _blank(size, dpr)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setBrush(QColor(tint))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(0, 0, round(size * dpr), round(size * dpr))
    p.end()
    return pm


def element_pixmap(elem: str, size: int = 18, color: Optional[str] = None) -> QPixmap:
    return _element_pixmap(elem, size, color, device_ratio())


def element_icon(elem: str, size: int = 18, color: Optional[str] = None) -> QIcon:
    return QIcon(element_pixmap(elem, size, color))


@lru_cache(maxsize=128)
def _element_badge(elem: str, size: int, dpr: float) -> QPixmap:
    """左侧角色列表用的圆形元素徽标（浅色底 + 元素色图标）。"""
    color = theme.element_color(elem)
    pm = _blank(size, dpr)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    bg = QColor(color)
    bg.setAlpha(30)
    p.setBrush(bg)
    p.setPen(Qt.PenStyle.NoPen)
    edge = round(size * dpr)
    p.drawEllipse(0, 0, edge, edge)
    inner = max(8, int(size * 0.58))
    sub = _element_pixmap(elem, inner, color, dpr)
    off = (edge - round(inner * dpr)) // 2
    p.drawPixmap(off, off, sub)
    p.end()
    return pm


def element_badge(elem: str, size: int = 30) -> QPixmap:
    return _element_badge(elem, size, device_ratio())


@lru_cache(maxsize=4)
def app_icon() -> QIcon:
    """窗口/任务栏图标：蓝色圆角方块 + 白色元素符号。"""
    ic = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setBrush(QColor(theme.BLUE))
        p.setPen(Qt.PenStyle.NoPen)
        r = size * 0.22
        p.drawRoundedRect(QRectF(0, 0, size, size), r, r)
        src = _element_source("pyro")
        if src:
            inner = int(size * 0.56)
            sub = _render(recolor(src, "#ffffff"), inner, dpr=1.0)
            p.drawPixmap((size - inner) // 2, (size - inner) // 2, sub)
        p.end()
        ic.addPixmap(pm)
    return ic


ICON_SIZE_SM = QSize(14, 14)
ICON_SIZE = QSize(16, 16)
ICON_SIZE_LG = QSize(18, 18)
