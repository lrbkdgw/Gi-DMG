"""设计令牌与全局 QSS。

取值全部来自 HTML 版 style2.css 的 :root 变量与最终层叠结果（Google AI Studio
风格的浅色界面），以保证 EXE 与网页版观感一致。
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Dict

from PySide6.QtGui import QColor, QFont, QFontDatabase

# ------------------------------------------------------------------ 颜色令牌

CANVAS = "#f3f5f8"
SURFACE = "#ffffff"
SURFACE_SUBTLE = "#eef1f5"
SURFACE_HOVER = "#e7ebf1"
BORDER = "#dce1e8"
BORDER_SOFT = "#eceff4"
TEXT = "#2b2f36"
TEXT_STRONG = "#1f242b"
MUTED = "#5b6470"
MUTED_SOFT = "#7a838f"
BLUE = "#0b57d0"
BLUE_HOVER = "#0842a0"
BLUE_TINT = "#edf3ff"
BLUE_TINT_HOVER = "#dbe9ff"
BLUE_BORDER = "#d7e4fb"
DANGER = "#c5221f"
DANGER_TINT = "#fce8e6"
WARN = "#b06000"
WARN_TINT = "#fef7e0"
OK = "#137333"
OK_TINT = "#e6f4ea"
SCROLL = "#cbd1da"
SCROLL_HOVER = "#aeb7c3"

RADIUS_SM = 10
RADIUS_MD = 14
RADIUS_LG = 20
RADIUS_CARD = 24
CONTROL_H = 32

# ------------------------------------------------------------------ 阴影令牌
# 对应 HTML 版 --studio-shadow / --studio-shadow-float，用于 QGraphicsDropShadowEffect。
# 每个元组是 (blur, dy, QColor)，供 widgets.shadow() / 悬浮抬升动画取用。
SHADOW_REST = (22, 4, QColor(22, 31, 48, 18))
SHADOW_HOVER = (34, 10, QColor(24, 37, 59, 40))
SHADOW_FLOAT = (40, 14, QColor(24, 37, 59, 48))
# 输入控件聚焦时的蓝色辉光（近似 CSS 的 0 0 0 3px rgba(11,87,208,.13) 焦点环）。
FOCUS_GLOW = QColor(11, 87, 208, 110)

# 全局动效开关。默认开启；离屏截图（tools/dev_preview.py）会临时关掉，
# 以便一次性抓到动画的终态，而不是中间帧。
ANIMATIONS = True

# 元素配色（与 HTML EL 表一致）
ELEMENT_COLORS = {
    "pyro": "#d75a3a",
    "hydro": "#2a7fbe",
    "electro": "#7d55c7",
    "cryo": "#3a9db8",
    "dendro": "#5a9a3a",
    "anemo": "#2b9b7f",
    "geo": "#b88a2d",
    "physical": "#6a5f57",
}
REACTION_COLOR = "#e67e22"


def element_color(key: str) -> str:
    return ELEMENT_COLORS.get(key, MUTED)


def tint(hex_color: str, alpha: int = 28) -> QColor:
    c = QColor(hex_color)
    c.setAlpha(alpha)
    return c


def mix(hex_color: str, other: str, ratio: float) -> str:
    a, b = QColor(hex_color), QColor(other)
    r = lambda x, y: round(x + (y - x) * ratio)
    return QColor(r(a.red(), b.red()), r(a.green(), b.green()), r(a.blue(), b.blue())).name()


# ------------------------------------------------------------------ 字体

_UI_FAMILIES = [
    "Google Sans", "Google Sans Text", "Microsoft YaHei UI", "Microsoft YaHei",
    "PingFang SC", "Noto Sans CJK SC", "Source Han Sans SC", "Segoe UI", "Sans Serif",
]
_MONO_FAMILIES = ["Cascadia Mono", "Consolas", "JetBrains Mono", "DejaVu Sans Mono", "Menlo", "Monospace"]


def _first_available(candidates: list[str], fallback: str) -> str:
    have = set(QFontDatabase.families())
    for name in candidates:
        if name in have:
            return name
    return fallback


def ui_font(size: float = 12.0, weight: int = QFont.Weight.Normal) -> QFont:
    f = QFont(_first_available(_UI_FAMILIES, "Sans Serif"))
    f.setPointSizeF(size)
    f.setWeight(weight)
    return f


def mono_font(size: float = 11.0) -> QFont:
    f = QFont(_first_available(_MONO_FAMILIES, "Monospace"))
    f.setPointSizeF(size)
    return f


def font_stack() -> str:
    fams = [f'"{n}"' for n in _UI_FAMILIES]
    return ", ".join(fams)


# ------------------------------------------------------------------ QSS 用小图标
# QSS 的 image:url() 需要真实文件；这里把 lucide 的勾选/箭头图标按主题色重新着色
# 后写到临时目录，让复选框有真正的对勾、下拉框有和网页版一致的 chevron 箭头。

_QSS_ASSETS: Dict[str, str] = {}


def _qss_assets() -> Dict[str, str]:
    if _QSS_ASSETS:
        return _QSS_ASSETS
    default = {"chevron": "", "chevron_disabled": "", "check": ""}
    try:
        from . import icons

        cache = Path(tempfile.gettempdir()) / "gidmg_qss_assets"
        cache.mkdir(parents=True, exist_ok=True)

        def _write(name: str, color: str, out: str) -> str:
            svg = icons.recolor(icons._svg_source(name), color)
            path = cache / out
            path.write_text(svg, encoding="utf-8")
            return path.as_posix()

        _QSS_ASSETS.update(
            chevron=_write("chevron-down", MUTED_SOFT, "chevron.svg"),
            chevron_disabled=_write("chevron-down", "#b6bdc7", "chevron-disabled.svg"),
            check=_write("check", "#ffffff", "check.svg"),
        )
    except Exception:  # pragma: no cover - 缺资源时退回原生控件外观
        _QSS_ASSETS.update(default)
    return _QSS_ASSETS


# ------------------------------------------------------------------ 全局 QSS

def stylesheet() -> str:
    assets = _qss_assets()
    chevron = assets.get("chevron", "")
    chevron_dis = assets.get("chevron_disabled", "")
    check = assets.get("check", "")
    combo_arrow = (
        f"QComboBox::down-arrow {{ image: url({chevron}); width: 14px; height: 14px; }}\n"
        f"QComboBox::down-arrow:disabled {{ image: url({chevron_dis}); }}\n"
        if chevron else ""
    )
    check_img = (
        f"QCheckBox::indicator:checked {{ image: url({check}); }}\n"
        if check else ""
    )
    return f"""
* {{ outline: none; }}

QWidget {{
    color: {TEXT};
    font-family: {font_stack()};
    font-size: 12px;
}}

QWidget#Root, QWidget#Canvas {{ background: {CANVAS}; }}
QWidget#Surface {{ background: {SURFACE}; }}

QToolTip {{
    background: #2b2f36; color: #ffffff; border: none;
    border-radius: 6px; padding: 5px 8px; font-size: 11px;
}}

/* ------------------------------------------------ 卡片 */
QFrame#Card {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_CARD}px;
}}
QFrame#SubCard {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_MD}px;
}}
QFrame#SoftCard {{
    background: {SURFACE_SUBTLE};
    border: 1px solid transparent;
    border-radius: {RADIUS_MD}px;
}}
QFrame#ResultsCard {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 18px;
}}
QFrame#Divider {{ background: {BORDER}; border: none; max-height: 1px; min-height: 1px; }}
QFrame#VDivider {{ background: {BORDER}; border: none; max-width: 1px; min-width: 1px; }}

/* ------------------------------------------------ 文字 */
QLabel#Kicker {{
    color: {MUTED}; font-size: 10px; font-weight: 700; letter-spacing: 1px;
}}
QLabel#Heading {{ color: {TEXT}; font-size: 20px; font-weight: 700; }}
QLabel#SubHeading {{ color: {TEXT}; font-size: 15px; font-weight: 700; }}
QLabel#Copy {{ color: {MUTED}; font-size: 12px; }}
QLabel#Muted {{ color: {MUTED}; font-size: 11px; }}
QLabel#FieldLabel {{ color: #4b5562; font-size: 11.5px; font-weight: 600; }}
QLabel#Danger {{ color: {DANGER}; font-size: 11px; }}
QLabel#Metric {{ color: {BLUE}; font-size: 18px; font-weight: 700; }}
QLabel#MetricSmall {{ color: {BLUE}; font-size: 15px; font-weight: 700; }}

/* ------------------------------------------------ 输入控件（对应 .pi） */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QTextEdit {{
    min-height: {CONTROL_H}px;
    padding: 0 10px;
    color: {TEXT};
    background: {SURFACE_SUBTLE};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_SM}px;
    selection-background-color: {BLUE};
    selection-color: #ffffff;
    font-size: 12px;
}}
QPlainTextEdit, QTextEdit {{ padding: 8px 10px; }}
QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover {{
    background: #edf1f7; border-color: #d4d9e1;
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus,
QPlainTextEdit:focus, QTextEdit:focus {{
    background: {SURFACE}; border-color: {BLUE};
}}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {{
    color: #a4acb7; background: #f2f4f7; border-color: {BORDER_SOFT};
}}
QLineEdit[invalid="true"], QSpinBox[invalid="true"], QDoubleSpinBox[invalid="true"] {{
    border-color: {DANGER}; background: {DANGER_TINT};
}}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 0; border: none; }}

QComboBox::drop-down {{ width: 28px; border: none; padding-right: 6px; }}
{combo_arrow}QComboBox QAbstractItemView {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_MD}px;
    padding: 5px;
    outline: none;
    selection-background-color: {BLUE_TINT};
    selection-color: {BLUE};
}}
QComboBox QAbstractItemView::item {{ min-height: 28px; padding: 4px 9px; border-radius: 8px; }}
QComboBox QAbstractItemView::item:hover {{ background: {SURFACE_SUBTLE}; }}

/* ------------------------------------------------ 按钮 */
QPushButton {{
    min-height: {CONTROL_H}px;
    padding: 0 14px;
    color: #3d4652;
    background: {SURFACE_SUBTLE};
    border: 1px solid {BORDER};
    border-radius: 999px;
    font-size: 12px;
    font-weight: 500;
}}
QPushButton:hover {{ background: {SURFACE_HOVER}; color: {TEXT}; }}
QPushButton:pressed {{ background: #dfe4ec; }}
QPushButton:disabled {{ color: #aab1bb; background: #f2f4f7; border-color: {BORDER_SOFT}; }}

QPushButton#Primary {{ color: #ffffff; background: {BLUE}; border-color: {BLUE}; font-weight: 600; }}
QPushButton#Primary:hover {{ background: {BLUE_HOVER}; border-color: {BLUE_HOVER}; }}
QPushButton#Primary:pressed {{ background: #06316f; }}
QPushButton#Primary:disabled {{ color: #eef1f5; background: #9db7e4; border-color: #9db7e4; }}

QPushButton#Tonal {{ color: {BLUE}; background: {BLUE_TINT}; border-color: {BLUE_BORDER}; font-weight: 600; }}
QPushButton#Tonal:hover {{ background: {BLUE_TINT_HOVER}; }}

QPushButton#DangerBtn {{ color: {DANGER}; background: {DANGER_TINT}; border-color: #f7cfcb; font-weight: 600; }}
QPushButton#DangerBtn:hover {{ background: #f9d6d3; }}

QPushButton#Ghost {{ color: {MUTED}; background: transparent; border-color: transparent; }}
QPushButton#Ghost:hover {{ color: {TEXT}; background: {SURFACE_SUBTLE}; }}

QPushButton#Link {{
    min-height: 18px; padding: 0 2px; color: {BLUE}; background: transparent;
    border: none; font-size: 11px; font-weight: 700;
}}
QPushButton#Link:hover {{ color: {BLUE_HOVER}; }}

QPushButton#Chip {{
    min-height: 24px; padding: 0 10px; color: #4f5966; background: {SURFACE_SUBTLE};
    border: 1px solid transparent; border-radius: 999px; font-size: 10.5px; font-weight: 500;
}}
QPushButton#Chip:hover {{ color: {BLUE}; background: {BLUE_TINT}; }}
QPushButton#Chip:checked {{ color: {BLUE}; background: {BLUE_TINT}; border-color: {BLUE_BORDER}; font-weight: 600; }}

QPushButton#IconBtn {{
    min-width: 30px; max-width: 30px; min-height: 30px; max-height: 30px;
    padding: 0; background: transparent; border: 1px solid transparent; border-radius: 15px;
}}
QPushButton#IconBtn:hover {{ background: {SURFACE_SUBTLE}; }}
QPushButton#IconBtn:pressed {{ background: {SURFACE_HOVER}; }}
QPushButton#IconBtn:checked {{ background: {BLUE_TINT}; }}

QPushButton#AddBtn {{
    min-width: 30px; max-width: 30px; min-height: 30px; max-height: 30px; padding: 0;
    background: {BLUE_TINT}; border: 1px solid {BLUE_BORDER}; border-radius: 15px;
}}
QPushButton#AddBtn:hover {{ background: {BLUE_TINT_HOVER}; }}

QPushButton#NavEntry {{
    min-height: 38px; padding: 0 10px; color: #4f5966; background: transparent;
    border: 1px solid transparent; border-radius: {RADIUS_SM}px;
    font-size: 12.5px; font-weight: 600; text-align: left;
}}
QPushButton#NavEntry:hover {{ background: {SURFACE_SUBTLE}; color: {TEXT}; }}
QPushButton#NavEntry:checked {{ background: {BLUE_TINT}; color: {BLUE}; border-color: {BLUE_BORDER}; }}

/* ------------------------------------------------ 滚动条 */
QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }}
QScrollBar:vertical {{ width: 8px; background: transparent; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {SCROLL}; border-radius: 4px; min-height: 28px; }}
QScrollBar::handle:vertical:hover {{ background: {SCROLL_HOVER}; }}
QScrollBar:horizontal {{ height: 8px; background: transparent; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {SCROLL}; border-radius: 4px; min-width: 28px; }}
QScrollBar::handle:horizontal:hover {{ background: {SCROLL_HOVER}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; border: none; background: none; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}

/* ------------------------------------------------ 表格 */
QTableView, QTableWidget {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: {RADIUS_MD}px;
    gridline-color: {BORDER_SOFT}; selection-background-color: {BLUE_TINT};
    selection-color: {TEXT}; font-size: 12px;
}}
QTableView::item, QTableWidget::item {{ padding: 6px 8px; border: none; }}
QHeaderView {{ background: transparent; border: none; }}
QHeaderView::section {{
    padding: 8px 10px; color: {MUTED}; background: {SURFACE_SUBTLE};
    border: none; border-bottom: 1px solid {BORDER}; font-size: 11.5px; font-weight: 700;
}}
QTableCornerButton::section {{ background: {SURFACE_SUBTLE}; border: none; }}

/* ------------------------------------------------ 列表 / 树 */
QListWidget, QTreeWidget {{
    background: transparent; border: none; outline: none;
}}
QListWidget::item {{ border-radius: {RADIUS_SM}px; padding: 2px; }}
QListWidget::item:selected {{ background: {BLUE_TINT}; color: {BLUE}; }}

/* ------------------------------------------------ 其它 */
QCheckBox {{ spacing: 8px; font-size: 12px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px; border: 1.5px solid #9aa3af;
    border-radius: 5px; background: {SURFACE};
}}
QCheckBox::indicator:checked {{ background: {BLUE}; border-color: {BLUE}; }}
{check_img}QCheckBox::indicator:hover {{ border-color: {BLUE}; }}
QCheckBox::indicator:checked:hover {{ background: {BLUE_HOVER}; border-color: {BLUE_HOVER}; }}
QCheckBox::indicator:disabled {{ border-color: #d3d8e0; background: #f2f4f7; }}

QProgressBar {{
    min-height: 8px; max-height: 8px; background: {SURFACE_SUBTLE};
    border: none; border-radius: 4px; text-align: center; color: transparent;
}}
QProgressBar::chunk {{ background: {BLUE}; border-radius: 4px; }}

QMenu {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: {RADIUS_SM}px; padding: 6px;
}}
QMenu::item {{ padding: 7px 14px 7px 12px; border-radius: 7px; font-size: 12px; color: #3d4652; }}
QMenu::item:selected {{ background: {SURFACE_SUBTLE}; color: {TEXT}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 5px 6px; }}

QSplitter::handle {{ background: {BORDER}; }}
QSplitter::handle:horizontal {{ width: 1px; }}

QDialog {{ background: {SURFACE}; }}
"""
