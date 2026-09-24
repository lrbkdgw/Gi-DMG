"""中央工作区：魔物设置。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QLabel, QWidget

from ..core import state as st
from ..core.constants import EL
from . import icons, theme, widgets as W
from .session import Session
from .widgets import hbox, label, vbox


class MonsterPanel(QWidget):
    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self.s = session
        lay = vbox(self, (0, 0, 0, 0), 0)

        card = W.Card(padding=20, spacing=0)
        lay.addWidget(card)
        lay.addStretch(1)

        card.add(label("TARGET CONFIGURATION", "Kicker"))
        card.add(label("魔物设置", "Heading"))
        card.add(label("设置目标等级与各元素抗性，所有伤害来源会即时按该目标重新结算。", "Copy", wrap=True))
        card.body.addSpacing(14)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(18)
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)
        card.add_layout(grid)

        # ---------------- 等级
        lv_card = W.SoftCard(padding=16, spacing=8)
        lv_card.setFixedWidth(214)
        lv_card.add(label("魔物等级", "FieldLabel"))
        self.level = W.NumField(self._enemy().get("level", 93), 93, decimals=0, allow_negative=False)
        self.level.edited.connect(self._set_level)
        lv_card.add(self.level)
        lv_card.add(label("影响防御区计算。支持 1–120 级目标。", "Muted", wrap=True))
        grid.addWidget(lv_card, 0, 0, Qt.AlignmentFlag.AlignTop)

        # ---------------- 抗性
        res_card = W.SoftCard(padding=16, spacing=10)
        res_card.add(label("元素抗性 %", "FieldLabel"))
        res_grid = QGridLayout()
        res_grid.setContentsMargins(0, 0, 0, 0)
        res_grid.setHorizontalSpacing(10)
        res_grid.setVerticalSpacing(8)
        res_card.add_layout(res_grid)

        self.res_fields = {}
        for i, e in enumerate(EL):
            cell = QWidget()
            cl = hbox(cell, (0, 0, 0, 0), 7)
            ic = QLabel()
            ic.setPixmap(icons.element_pixmap(e["id"], 16))
            ic.setFixedWidth(18)
            cl.addWidget(ic, 0, Qt.AlignmentFlag.AlignVCenter)
            nm = label(e["n"])
            nm.setStyleSheet(f"color:{theme.MUTED};font-size:11.5px;")
            nm.setFixedWidth(30)
            cl.addWidget(nm, 0, Qt.AlignmentFlag.AlignVCenter)
            fld = W.NumField(self._res().get(e["id"], 10), 10, decimals=2)
            fld.edited.connect(lambda _v, k=e["id"]: self._set_res(k))
            self.res_fields[e["id"]] = fld
            cl.addWidget(fld, 1)
            res_grid.addWidget(cell, i // 2, i % 2)

        res_card.add(label("负抗性按 1 - res/200 计算；超过 75% 按 1/(4·res/100 + 1) 递减。",
                           "Muted", wrap=True))
        grid.addWidget(res_card, 0, 1)

        session.calcFinished.connect(self._sync)

    # ------------------------------------------------------------------

    def _enemy(self):
        return self.s.state.setdefault("enemy", {"level": 93, "res": {}})

    def _res(self):
        return self._enemy().setdefault("res", {})

    def _set_level(self, _v: float) -> None:
        self._enemy()["level"] = self.level.value()
        self.s.touch()

    def _set_res(self, key: str) -> None:
        self._res()[key] = self.res_fields[key].value()
        self.s.touch()

    def _sync(self) -> None:
        if not self.isVisible():
            return
        if not self.level.hasFocus():
            self.level.set_value(self._enemy().get("level", 93))
        for k, f in self.res_fields.items():
            if not f.hasFocus():
                f.set_value(self._res().get(k, 10))
