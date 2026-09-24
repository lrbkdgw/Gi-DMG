"""配置管理界面 —— EXE 启动后的第一屏。

对应 What_Change.md 第 2 条：从 date/ 里挑一个已有配置进入，或者新建一个。
右上角保留了「计算公式」入口（第 3 条：公式按钮移动到配置管理界面）。
"""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (QFileDialog, QFrame, QHBoxLayout, QInputDialog, QLabel,
                               QMenu, QMessageBox, QSizePolicy, QVBoxLayout, QWidget)

from ..core import state as st
from ..core.format import rounded
from ..core.storage import ConfigMeta, Storage
from . import icons, theme, widgets as W
from .widgets import button, chip, clear_layout, hbox, icon_button, label, vbox


class ConfigCard(QFrame):
    """配置列表里的一行。"""

    opened = Signal(str)
    renamed = Signal(str)
    duplicated = Signal(str)
    deleted = Signal(str)
    exported = Signal(str)

    def __init__(self, meta: ConfigMeta, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.meta = meta
        self.setObjectName("ConfigCard")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet(f"""
            QFrame#ConfigCard {{
                background: {theme.SURFACE}; border: 1px solid {theme.BORDER};
                border-radius: 16px;
            }}
            QFrame#ConfigCard:hover {{ border-color: {theme.BLUE_BORDER}; background: #fbfcfe; }}
        """)
        lay = hbox(self, (16, 13, 12, 13), 12)

        badge = QLabel()
        badge.setFixedSize(38, 38)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setPixmap(icons.pixmap("folder", 17, theme.BLUE))
        badge.setStyleSheet(f"background:{theme.BLUE_TINT};border-radius:12px;")
        lay.addWidget(badge, 0, Qt.AlignmentFlag.AlignVCenter)

        col = vbox(spacing=3)
        title_row = hbox(spacing=6)
        name = label(meta.name)
        name.setStyleSheet(f"color:{theme.TEXT};font-size:13.5px;font-weight:700;")
        title_row.addWidget(name)
        if meta.has_draft:
            draft = W.Pill("未保存草稿", theme.WARN, theme.WARN_TINT)
            title_row.addWidget(draft)
        title_row.addStretch(1)
        col.addLayout(title_row)

        bits = [meta.chars_text, f"轴长 {meta.rotation:g}s" if meta.timeline else "未开启时间轴"]
        if meta.total:
            bits.append(f"总期望 {rounded(meta.total)}")
        sub = label(" · ".join(bits), "Muted")
        sub.setStyleSheet(f"color:{theme.MUTED};font-size:11px;")
        col.addWidget(sub)
        lay.addLayout(col, 1)

        time_lb = label(meta.saved_text, "Muted")
        time_lb.setStyleSheet(f"color:{theme.MUTED_SOFT};font-size:10.5px;")
        lay.addWidget(time_lb, 0, Qt.AlignmentFlag.AlignVCenter)

        more = icon_button("ellipsis", "更多操作", self)
        more.clicked.connect(self._menu)
        lay.addWidget(more, 0, Qt.AlignmentFlag.AlignVCenter)

        enter = button("打开", "chevron-right", "Tonal", self,
                       lambda: self.opened.emit(self.meta.name))
        lay.addWidget(enter, 0, Qt.AlignmentFlag.AlignVCenter)

        W.attach_hover_lift(self, active=(26, 7, theme.tint("#182533", 34)))

    def mouseDoubleClickEvent(self, ev) -> None:
        self.opened.emit(self.meta.name)
        ev.accept()

    def _menu(self) -> None:
        m = QMenu(self)
        m.addAction(icons.muted("pencil", 14), "重命名", lambda: self.renamed.emit(self.meta.name))
        m.addAction(icons.muted("copy", 14), "创建副本", lambda: self.duplicated.emit(self.meta.name))
        m.addAction(icons.muted("upload", 14), "导出为 JSON", lambda: self.exported.emit(self.meta.name))
        m.addSeparator()
        act = m.addAction(icons.icon("trash-2", 14, theme.DANGER), "删除配置",
                          lambda: self.deleted.emit(self.meta.name))
        act.setIconVisibleInMenu(True)
        m.exec(QCursor.pos())


class LauncherView(QWidget):
    """配置管理页。"""

    openConfig = Signal(str)          # 打开已有配置
    createConfig = Signal(str, dict)  # 新建配置（名称, 初始状态）
    showFormula = Signal()

    def __init__(self, storage: Storage, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.storage = storage
        self.setObjectName("Canvas")

        outer = vbox(self, (0, 0, 0, 0), 0)

        scroll = W.ScrollArea(margins=(0, 0, 0, 0))
        outer.addWidget(scroll, 1)

        page = QWidget()
        page.setMaximumWidth(980)
        page.setMinimumWidth(560)
        page_lay = vbox(page, (32, 36, 32, 48), 0)
        holder = hbox(spacing=0)
        holder.addStretch(1)
        holder.addWidget(page, 1000)
        holder.addStretch(1)
        scroll.body.addLayout(holder)

        # ---------------- 顶部标题栏
        head = hbox(spacing=12)
        title_col = vbox(spacing=4)
        title_col.addWidget(label("GENSHIN DAMAGE CALCULATOR", "Kicker"))
        h = label("配置管理")
        h.setStyleSheet(f"color:{theme.TEXT};font-size:27px;font-weight:700;")
        title_col.addWidget(h)
        title_col.addWidget(label("选择一份已有配置继续，或新建一份。所有配置都保存在程序目录的 date 文件夹里。",
                                  "Copy", wrap=True))
        head.addLayout(title_col, 1)

        tools = hbox(spacing=6)
        tools.setAlignment(Qt.AlignmentFlag.AlignTop)
        tools.addWidget(icon_button("sigma", "计算公式", self, self.showFormula.emit, size=17))
        tools.addWidget(icon_button("download", "导入配置文件", self, self._import))
        tools.addWidget(icon_button("folder-open", "打开 date 文件夹", self, self._open_folder))
        head.addLayout(tools, 0)
        page_lay.addLayout(head)
        page_lay.addSpacing(22)

        # ---------------- 新建区
        page_lay.addWidget(self._new_section())
        page_lay.addSpacing(24)

        # ---------------- 已有配置
        list_head = hbox(spacing=8)
        self.count_label = label("已有配置", "SubHeading")
        self.count_label.setStyleSheet(f"color:{theme.TEXT};font-size:15px;font-weight:700;")
        list_head.addWidget(self.count_label)
        list_head.addStretch(1)
        list_head.addWidget(button("刷新", "refresh-cw", "", self, self.reload))
        page_lay.addLayout(list_head)
        page_lay.addSpacing(10)

        self.list_host = QWidget()
        self.list_lay = vbox(self.list_host, (0, 0, 0, 0), 8)
        page_lay.addWidget(self.list_host)
        page_lay.addStretch(1)

        # ---------------- 底部路径提示
        foot = hbox(spacing=6)
        path_lb = label(f"数据目录：{self.storage.root}", "Muted")
        path_lb.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        foot.addWidget(path_lb)
        foot.addStretch(1)
        page_lay.addSpacing(18)
        page_lay.addLayout(foot)

        self.reload()

    # ------------------------------------------------------------------ 子区块

    def _new_section(self) -> QWidget:
        card = W.Card(padding=18, spacing=14)
        row = hbox(spacing=10)
        col = vbox(spacing=3)
        col.addWidget(label("新建配置", "SubHeading"))
        col.addWidget(label("从空白开始，或直接载入一个示例队伍。", "Muted"))
        row.addLayout(col, 1)
        row.addWidget(button("空白配置", "file-plus", "Primary", card,
                             lambda: self._create("新配置", None)))
        card.add_layout(row)

        card.add(W.HLine())

        tmpl_label = label("示例模板", "Muted")
        card.add(tmpl_label)

        host = QWidget()
        flow = W.FlowLayout(host, h_spacing=6, v_spacing=6)
        for key, title, desc in (
            ("vape", "胡桃 + 夜兰 · 蒸发", ("hutao", "yelan")),
            ("quicken", "纳西妲 + 雷电将军 · 超绽放", ("nahida", "raiden")),
            ("hutao", "单人 · 胡桃", ("hutao",)),
            ("nahida", "单人 · 纳西妲", ("nahida",)),
        ):
            flow.addWidget(chip(title, host, lambda d=desc, t=title: self._create(t, d),
                                icon_name="sparkles"))
        card.add(host)
        return card

    # ------------------------------------------------------------------ 行为

    def reload(self) -> None:
        clear_layout(self.list_lay)
        metas: List[ConfigMeta] = self.storage.list_configs()
        self.count_label.setText(f"已有配置（{len(metas)}）" if metas else "已有配置")
        if not metas:
            self.list_lay.addWidget(W.EmptyState(
                "folder", "date 文件夹里还没有配置",
                "点击上面的「空白配置」新建一份，或用右上角的导入按钮载入 JSON。"))
            return
        for i, meta in enumerate(metas):
            card = ConfigCard(meta, self.list_host)
            card.opened.connect(self.openConfig.emit)
            card.renamed.connect(self._rename)
            card.duplicated.connect(self._duplicate)
            card.deleted.connect(self._delete)
            card.exported.connect(self._export)
            self.list_lay.addWidget(card)
            # 逐张错峰淡入，进入配置管理页时有轻盈的列表铺开感。
            W.fade_in(card, duration=260, delay=min(i, 8) * 45, start=0.0)

    def _create(self, default_name: str, presets) -> None:
        name, ok = QInputDialog.getText(self, "新建配置", "配置名称：", text=default_name)
        if not ok:
            return
        state = st.def_state()
        if presets:
            state["chars"] = [st.build_preset(k) for k in presets if st.build_preset(k)]
            state["selId"] = state["chars"][0]["id"] if state["chars"] else None
        self.createConfig.emit(name.strip() or default_name, state)

    def _rename(self, name: str) -> None:
        new, ok = QInputDialog.getText(self, "重命名配置", "新的名称：", text=name)
        if ok and new.strip():
            self.storage.rename_config(name, new.strip())
            self.reload()

    def _duplicate(self, name: str) -> None:
        self.storage.duplicate_config(name)
        self.reload()

    def _delete(self, name: str) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("删除配置")
        box.setText(f"确定删除配置「{name}」吗？")
        box.setInformativeText("该操作不可撤销，对应的 JSON 文件会从 date/configs 中移除。")
        box.setIcon(QMessageBox.Icon.Warning)
        yes = box.addButton("删除", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("取消", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is yes:
            self.storage.delete_config(name)
            self.reload()

    def _export(self, name: str) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "导出配置", f"{name}.json", "JSON 文件 (*.json)")
        if path:
            self.storage.export_config(name, path)

    def _import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "导入配置", "", "JSON 文件 (*.json)")
        if not path:
            return
        try:
            self.storage.import_config(path)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "导入失败", f"无法读取该文件：\n{exc}")
            return
        self.reload()

    def _open_folder(self) -> None:
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        self.storage.ensure()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.storage.root)))
