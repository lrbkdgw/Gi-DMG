"""设计令牌与全局 QSS。

取值全部来自 HTML 版 style2.css 的 :root 变量与最终层叠结果（Google AI Studio
风格的浅色界面），以保证 EXE 与网页版观感一致。
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QFontDatabase

# ------------------------------------------------------------------ 颜色令牌

CANVAS = "#f3f5f8"
SURFACE = "#ffffff"
SURFACE_SUBTLE = "#eef1f5"
SURFACE_HOVER = "#e7ebf1"
BORDER = "#e2e5eb"
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


# ------------------------------------------------------------------ 全局 QSS

def stylesheet() -> str:
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
    font-size: 11.5px;
}}
QLineEdit {{ placeholder-text-color: #8a94a2; }}
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

QComboBox::drop-down {{ width: 26px; border: none; }}
QComboBox QAbstractItemView {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_SM}px;
    padding: 4px;
    margin: 0px;
    outline: none;
    selection-background-color: {BLUE_TINT};
    selection-color: {BLUE};
}}
QComboBox QAbstractItemView::item {{ min-height: 30px; padding: 6px 8px; border-radius: 8px; font-size: 11px; }}

/* ------------------------------------------------ 按钮 */
/* 颜色过渡由 widgets.MotionButton 自绘完成（对应 CSS transition），
   这里只声明几何与字体，尺寸取自 HTML 最终层叠结果。 */
QPushButton {{
    min-height: 30px;
    padding: 0 12px;
    color: #4f5a67;
    background: transparent;
    border: 1px solid {BORDER};
    border-radius: 999px;
    font-size: 11.5px;
    font-weight: 500;
}}

QPushButton#Primary {{
    min-height: 32px; padding: 0 13px; color: #ffffff;
    background: {BLUE}; border-color: {BLUE}; font-size: 11.5px; font-weight: 600;
}}

QPushButton#Tonal {{
    min-height: 32px; padding: 0 13px; color: {BLUE};
    background: {BLUE_TINT}; border-color: {BLUE_BORDER}; font-size: 11.5px; font-weight: 600;
}}

QPushButton#DangerBtn {{
    min-height: 30px; padding: 0 12px; color: {DANGER};
    background: {DANGER_TINT}; border-color: #f7cfcb; font-size: 11.5px; font-weight: 600;
}}

QPushButton#Ghost {{
    min-height: 30px; padding: 0 9px; color: #647080;
    background: transparent; border-color: transparent; font-size: 11px;
}}

QPushButton#Link {{
    min-height: 18px; padding: 0 3px; color: {BLUE}; background: transparent;
    border: none; font-size: 11px; font-weight: 700;
}}

QPushButton#Chip {{
    min-height: 24px; padding: 0 10px; color: #4f5966; background: {SURFACE_SUBTLE};
    border: 1px solid transparent; border-radius: 999px; font-size: 10.5px; font-weight: 500;
}}

QPushButton#IconBtn {{
    min-width: 30px; max-width: 30px; min-height: 30px; max-height: 30px;
    padding: 0; background: transparent; border: 1px solid transparent; border-radius: 15px;
}}

QPushButton#AddBtn {{
    min-width: 30px; max-width: 30px; min-height: 30px; max-height: 30px; padding: 0;
    background: {BLUE_TINT}; border: 1px solid {BLUE_BORDER}; border-radius: 15px;
}}

QPushButton#NavEntry {{
    min-height: 38px; padding: 0 12px; color: #4f5966; background: transparent;
    border: 1px solid transparent; border-radius: 19px;
    font-size: 12.5px; font-weight: 500; text-align: left;
}}

/* ------------------------------------------------ 滚动条 */
QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }}
QScrollBar:vertical {{ width: 6px; background: transparent; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {SCROLL}; border-radius: 3px; min-height: 28px; }}
QScrollBar::handle:vertical:hover {{ background: {SCROLL_HOVER}; }}
QScrollBar:horizontal {{ height: 6px; background: transparent; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {SCROLL}; border-radius: 3px; min-width: 28px; }}
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
QCheckBox {{ spacing: 7px; font-size: 12px; }}
QCheckBox::indicator {{
    width: 15px; height: 15px; border: 1.5px solid #9aa3af;
    border-radius: 4px; background: {SURFACE};
}}
QCheckBox::indicator:checked {{ background: {BLUE}; border-color: {BLUE}; }}
QCheckBox::indicator:hover {{ border-color: {BLUE}; }}

QProgressBar {{
    min-height: 8px; max-height: 8px; background: {SURFACE_SUBTLE};
    border: none; border-radius: 4px; text-align: center; color: transparent;
}}
QProgressBar::chunk {{ background: {BLUE}; border-radius: 4px; }}

QMenu {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px; padding: 6px;
}}
QMenu::item {{ padding: 8px 14px 8px 9px; border-radius: 9px; font-size: 11.5px; color: #43474e; }}
QMenu::item:selected {{ background: {BLUE_TINT}; color: {BLUE}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 5px 6px; }}

QSplitter::handle {{ background: {BORDER}; }}
QSplitter::handle:horizontal {{ width: 1px; }}

QDialog {{ background: {SURFACE}; }}
/* 自绘的无边框弹窗（dialogs.base.Modal）：窗体透明，卡片自己画圆角与阴影 */
QDialog#Modal {{ background: transparent; }}
QFrame#ModalCard {{ background: {SURFACE}; border: none; border-radius: {RADIUS_CARD}px; }}
"""
