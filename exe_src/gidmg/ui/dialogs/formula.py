"""计算公式总览（对应 HTML formulaModal）。

HTML 版用 KaTeX 排版，桌面版没有 LaTeX 引擎，改用等价的纯文本公式，内容一一对应。
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QWidget

from ...core.constants import FORMULA_REACTS
from ...core.engine import level_coeff
from .. import theme, widgets as W
from ..widgets import hbox, label, vbox
from .base import Modal

SECTIONS: List[Tuple[str, List[str], Optional[str]]] = [
    ("普通伤害",
     ["基础伤害 = 计入属性 × 倍率%",
      "最终伤害 = 基础伤害 × 伤害加成区 × 暴击区 × 防御区 × 抗性区 × 增幅区 × 独立乘区"],
     "计入属性可选「固定值」，此时 基础伤害 = 固定值 × 倍率%。"),
    ("增幅反应（蒸发 / 融化）",
     ["增幅区 = 基础倍率 × ( 1 + 2.78 × 精通 / (精通 + 1400) + 增幅反应加成% )"],
     None),
    ("剧变反应（不可暴击，不吃防御区与伤害加成）",
     ["伤害 = 等级系数 × 反应倍率 × ( 1 + 16 × 精通 / (精通 + 2000) + 剧变加成% ) × 抗性区"],
     "「段数」为该来源在单轮循环内的触发次数，来源总伤 = 单次伤害 × 段数。"),
    ("特殊直伤（月曜 / 星超导 / 星扩散）",
     ["伤害 = 计入属性 × 倍率% × 反应系数 × 基础区 × ( 1 + 6 × 精通 / (精通 + 2000) + 直伤加成% )",
      "　　　 × 暴击区 × 抗性区 × 擢升 × 独立乘区",
      "基础区 = 1 + 对应反应基础区%"],
     "月曜反应基础区 / 月感电、月绽放、月结晶基础区；星烁反应基础区 / 星超导、星扩散基础区，"
     "天赋默认作用于全队。该来源的全部伤害（含羽毛附加伤害）均乘基础区。"),
    ("特殊反应多角色贡献",
     ["月曜（月感电 / 月结晶）： w = ( 1 , 1/2 , 1/12 , 1/12 )",
      "星扩散（风）： w = ( 3/5 , 3/10 , 1/20 , 1/20 )",
      "星扩散（冰）： w = ( 3/5 , 3/10 , 1/20 , 1/20 )",
      "伤害 = Σ( 组分ᵢ × wᵢ )，i = 1…4",
      "组分 = 等级系数 × 反应倍率 × 基础区 × ( 1 + 6 × 精通 / (精通 + 2000) + 反应伤害加成% )",
      "　　　 × 暴击区 × 抗性区 × 擢升 × 独立乘区"],
     "月感电 / 月结晶：各参与角色分别计算组分，按伤害从高到低加权求和；仅 1 名参与角色时自然取 ×1。"
     "星扩散（风）：风元素参与角色中伤害最高 ×3/5（无风元素参与时该槽位为空），其余按伤害从高到低 "
     "×3/10、×1/20、×1/20。星扩散（冰）：挂冰角色中伤害最高 ×3/5、挂风角色中伤害最高 ×3/10，"
     "其余按伤害从高到低 ×1/20、×1/20。"),
    ("星超导 / 星扩散",
     ["星超导系数(n) = 1.00　（n = 0）",
      "星超导系数(n) = 1.45 + 0.05 × (n − 1)　（n ≥ 1）",
      "星扩散直伤系数 = 1 ，反应星扩散（冰） = 2/3 ，反应星扩散（风） = 0.75"],
     "星超导仅直伤，天赋可超过 12 层。角色星超导 / 角色星扩散直伤的伤害元素跟随伤害归属角色的元素"
     "（雷元素角色造成雷伤、风元素角色造成风伤）。"),
    ("羽毛效果",
     ["附加伤害 = 天赋所属角色面板属性 × 数值%　或　固定值"],
     "面板按天赋所属角色结算，而非羽毛目标伤害来源的计入角色。普通直伤并入基础伤害区；"
     "剧变吃精通 × 抗性；星 / 月反应吃基础区 × 抗性 × 暴击 × 曜升。"),
]


class FormulaDialog(Modal):
    def __init__(self, parent):
        super().__init__(parent, "计算公式总览", "sigma", width=720, height=680)
        for title, lines, note in SECTIONS:
            self.add(self._section(title, lines, note))
        self.add(self._level_section())
        self.finish_body()
        self.add_button("关闭", "", "Primary", self.accept)

    def _section(self, title: str, lines: List[str], note: Optional[str]) -> QWidget:
        card = W.SubCard(padding=14, spacing=8)
        card.add(label(title, "FieldLabel"))
        for line in lines:
            box = W.SoftCard(padding=9, spacing=0)
            fx = label(line, "Copy", wrap=True)
            fx.setStyleSheet(f"color:{theme.TEXT};font-size:12px;")
            fx.setFont(theme.mono_font(9))
            box.add(fx)
            card.add(box)
        if note:
            n = label(note, "Muted", wrap=True)
            card.add(n)
        return card

    def _level_section(self) -> QWidget:
        card = W.SubCard(padding=14, spacing=9)
        card.add(label("等级系数", "FieldLabel"))
        box = W.SoftCard(padding=9, spacing=0)
        fx = label("等级系数(lv) = c_lo + (c_hi − c_lo) × (lv − lv_lo) / (lv_hi − lv_lo)",
                   "Copy", wrap=True)
        fx.setFont(theme.mono_font(9))
        box.add(fx)
        card.add(box)

        head = hbox(spacing=8)
        head.addWidget(label("等级", "Muted"))
        head.addStretch(1)
        self.lv_badge = W.Pill("90", theme.BLUE, theme.BLUE_TINT)
        head.addWidget(self.lv_badge)
        card.add_layout(head)

        self.slider = W.Slider(Qt.Orientation.Horizontal)
        self.slider.setRange(1, 100)
        self.slider.setValue(90)
        self.slider.valueChanged.connect(self._update_lv)
        card.add(self.slider)

        self.coeff_lb = label("")
        self.coeff_lb.setStyleSheet(f"color:{theme.TEXT};font-size:12.5px;font-weight:700;")
        card.add(self.coeff_lb)

        grid_host = QWidget()
        self.grid = QGridLayout(grid_host)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(6)
        self.grid.setVerticalSpacing(6)
        self.cells = []
        for i, r in enumerate(FORMULA_REACTS):
            cell = W.SoftCard(padding=7, spacing=0)
            lb = label("", "Copy")
            lb.setStyleSheet(f"color:{theme.TEXT};font-size:11px;")
            cell.add(lb)
            self.cells.append((lb, r))
            self.grid.addWidget(cell, i // 3, i % 3)
        card.add(grid_host)
        self._update_lv(90)
        return card

    def _update_lv(self, lv: int) -> None:
        c = level_coeff(lv)
        self.lv_badge.setText(str(lv))
        self.coeff_lb.setText(f"等级系数：{c:.2f}")
        for lb, r in self.cells:
            lb.setText(f"{r['n']} ×{r['m']:g} = {c * r['m']:.1f}")


def open_formula(parent) -> None:
    FormulaDialog(parent).exec()
