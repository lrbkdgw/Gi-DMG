"""全局设置弹窗（对应 HTML settingsModal）。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from ...version import VERSION
from .. import theme, widgets as W
from ..session import Session
from ..widgets import hbox, label, vbox
from .base import Modal


class SettingsDialog(Modal):
    def __init__(self, parent, session: Session):
        super().__init__(parent, "全局设置", "settings", width=520, height=620, badge=f"v{VERSION}")
        self.s = session
        st = session.storage.load_settings()

        # -------- 时间轴
        box1 = W.SoftCard(padding=12, spacing=8)
        self.timeline = W.LabeledToggle(
            "开启循环时间轴模式", "按技能出伤时刻与持续时间动态结算 Buff",
            session.timeline_on)
        self.timeline.toggled.connect(self._on_timeline)
        box1.add(self.timeline)
        self.add(box1)

        box2 = W.SoftCard(padding=12, spacing=8)
        self.share = W.LabeledToggle(
            "开启伤害占比", "在伤害统计与拉表结果中分析各角色与反应的伤害占比",
            session.share_on)
        self.share.toggled.connect(self._on_share)
        box2.add(self.share)
        self.add(box2)

        # -------- 轴长
        self.rot_box = W.SoftCard(padding=12, spacing=6)
        self.rot_box.add(label("循环总轴长 (秒)", "FieldLabel"))
        self.rot = W.NumField(session.state.get("rotationDuration", 20), 20, decimals=2,
                              allow_negative=False)
        self.rot.edited.connect(self._on_rot)
        self.rot_box.add(self.rot)
        self.rot_box.add(label("若技能或 Buff 持续时间超过轴长，将自动循环并在下一轮继续生效。",
                               "Muted", wrap=True))
        self.rot_box.setVisible(session.timeline_on)
        self.add(self.rot_box)

        # -------- 历史记录
        box3 = W.SoftCard(padding=12, spacing=8)
        box3.add(label("历史记录", "FieldLabel"))
        self.cfg_hist = W.NumField(st.get("cfgHistCount", 5), 5, decimals=0)
        self.cfg_hist.edited.connect(self._on_hist)
        box3.add(W.field("配置历史保存次数（-1 为保存所有）", self.cfg_hist))
        self.qt_hist = W.NumField(st.get("qtHistCount", 10), 10, decimals=0)
        self.qt_hist.edited.connect(self._on_hist)
        box3.add(W.field("拉表结果保存次数（-1 为保存所有）", self.qt_hist))
        box3.add(label("退出配置时自动记录当前配置，完成快速拉表时自动保存结果；-1 表示不限制数量。",
                       "Muted", wrap=True))
        self.add(box3)

        # -------- 基准对比模式
        box4 = W.SoftCard(padding=12, spacing=8)
        row = hbox(spacing=10)
        col = vbox(spacing=2)
        col.addWidget(label("基准对比模式", "FieldLabel"))
        col.addWidget(label("切换当前配置与已保存基准的差异计算方向。", "Muted", wrap=True))
        row.addLayout(col, 1)
        self.mode_btn = W.button(self._mode_text(), "", "", box4, self._flip_mode)
        row.addWidget(self.mode_btn)
        box4.add_layout(row)
        self.add(box4)

        # -------- 数据目录
        box5 = W.SoftCard(padding=12, spacing=8)
        box5.add(label("数据目录", "FieldLabel"))
        p = label(str(session.storage.root), "Muted", wrap=True)
        p.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        box5.add(p)
        row5 = hbox(spacing=6)
        row5.addWidget(W.button("打开文件夹", "folder-open", "", box5, self._open_folder))
        row5.addStretch(1)
        box5.add_layout(row5)
        box5.add(label("全局设置、武器库、圣遗物库与所有配置都自动保存在这里。", "Muted", wrap=True))
        self.add(box5)

        self.finish_body()
        self.add_button("完成", "check", "Primary", self.accept)

    # ------------------------------------------------------------------

    def _mode_text(self) -> str:
        return "当前 vs 基准" if self.s.state.get("baselineMode", "a") == "a" else "基准 vs 当前"

    def _on_timeline(self, value: bool) -> None:
        self.s.state["timelineEnabled"] = value
        self.rot_box.setVisible(value)
        self.s.touch(editor=True, immediate=True)

    def _on_share(self, value: bool) -> None:
        self.s.state["dmgShareEnabled"] = value
        self.s.touch(immediate=True)

    def _on_rot(self, value: float) -> None:
        self.s.state["rotationDuration"] = value
        self.s.touch()

    def _on_hist(self, _v: float) -> None:
        self.s.storage.update_settings(cfgHistCount=int(self.cfg_hist.value()),
                                       qtHistCount=int(self.qt_hist.value()))

    def _flip_mode(self) -> None:
        self.s.state["baselineMode"] = "b" if self.s.state.get("baselineMode", "a") == "a" else "a"
        self.mode_btn.setText(self._mode_text())
        self.s.touch()

    def _open_folder(self) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        self.s.storage.ensure()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.s.storage.root)))


def open_settings(parent, session: Session) -> None:
    SettingsDialog(parent, session).exec()
