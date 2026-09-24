"""快速拉表：方案收集 → 组合计算（带进度）→ 结果表 / 排序 / 偏序剔除 / 导出。"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QFileDialog, QFrame, QHeaderView, QInputDialog, QMessageBox,
                               QTableWidget, QTableWidgetItem, QWidget)

from ...core import quicktable as qtc
from ...core.format import rounded
from .. import icons, theme, widgets as W
from ..session import Session
from ..widgets import button, chip, clear_layout, hbox, icon_button, label, vbox
from .base import Modal


class _Worker(QObject):
    """在后台线程里跑组合计算，避免界面卡死。"""

    progress = Signal(int, int)
    done = Signal(list)
    failed = Signal(str)

    def __init__(self, state: Dict[str, Any], schemes: Dict[str, List[qtc.Scheme]]):
        super().__init__()
        self.state = state
        self.schemes = schemes
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        try:
            rows = qtc.run(self.state, self.schemes, self._on_progress)
        except Exception as exc:  # 计算异常要能提示，不能静默
            self.failed.emit(str(exc))
            return
        self.done.emit(rows)

    def _on_progress(self, done: int, total: int) -> bool:
        self.progress.emit(done, total)
        return not self._cancel


class SchemeCollector(Modal):
    """拉表模式：为每个角色保存若干「方案」。"""

    def __init__(self, parent, session: Session, editor):
        super().__init__(parent, "快速拉表 · 收集方案", "table-properties", width=560, height=560)
        self.s = session
        self.editor = editor
        self.schemes: Dict[str, List[qtc.Scheme]] = {}

        tip = W.SoftCard(padding=12, spacing=6)
        tip.add(label("怎么用", "FieldLabel"))
        tip.add(label("1. 关掉这个窗口，在左侧切换角色、调整面板/武器/圣遗物；\n"
                      "2. 回到这里点「保存当前角色为方案」，给它一个名字和代价；\n"
                      "3. 每个角色可以存多个方案，未存方案的角色按当前面板参与；\n"
                      "4. 点「开始计算」枚举所有组合。", "Copy", wrap=True))
        self.add(tip)

        row = hbox(spacing=8)
        row.addWidget(button("保存当前角色为方案", "circle-plus", "Tonal", self, self._save_scheme))
        row.addStretch(1)
        self.count_lb = label("", "Muted")
        row.addWidget(self.count_lb)
        self.body.addLayout(row)

        self.list_host = QWidget()
        self.list_lay = vbox(self.list_host, (0, 0, 0, 0), 6)
        self.add(self.list_host, 1)

        self.add_button("取消", "", "", self.reject)
        self.run_btn = self.add_button("开始计算", "play", "Primary", self._start)
        self.refresh()

    def refresh(self) -> None:
        clear_layout(self.list_lay)
        total = qtc.count_combinations(qtc.build_options(self.s.state, self.schemes))
        n_schemes = sum(len(v) for v in self.schemes.values())
        self.count_lb.setText(f"共 {n_schemes} 个方案 · {total} 种组合")
        self.run_btn.setEnabled(total > 0)

        if not self.schemes:
            lb = label("尚未保存任何方案。直接开始计算的话，每个启用角色都按当前面板参与。",
                       "Muted", wrap=True)
            lb.setStyleSheet(f"color:{theme.MUTED_SOFT};font-size:11.5px;padding:10px 2px;")
            self.list_lay.addWidget(lb)
        for char_id, items in self.schemes.items():
            c = self.s.char(char_id)
            head = label(f"{c.get('name','?') if c else '?'}（{len(items)} 个方案）", "FieldLabel")
            self.list_lay.addWidget(head)
            for sc in items:
                f = QFrame()
                f.setStyleSheet(f"QFrame {{ background:{theme.SURFACE_SUBTLE}; border-radius:10px; }}")
                fl = hbox(f, (10, 6, 8, 6), 8)
                fl.addWidget(label(sc.name), 1)
                fl.addWidget(W.Pill(f"代价 {sc.cost:g}", theme.WARN, theme.WARN_TINT))
                fl.addWidget(icon_button("x", "删除方案", f,
                                         lambda s=sc, cid=char_id: self._remove(cid, s), size=13))
                self.list_lay.addWidget(f)
        self.list_lay.addStretch(1)

    def _save_scheme(self) -> None:
        ch = self.s.selected
        if ch is None:
            QMessageBox.information(self, "快速拉表", "请先在左侧选择一个角色。")
            return
        existing = self.schemes.get(ch["id"], [])
        name, ok = QInputDialog.getText(self, "保存方案", "方案名称：",
                                        text=f"方案 {len(existing) + 1}")
        if not ok:
            return
        cost, ok = QInputDialog.getDouble(self, "保存方案", "方案代价（数值）：", 0, -1e9, 1e9, 2)
        if not ok:
            return
        self.schemes.setdefault(ch["id"], []).append(
            qtc.Scheme(ch["id"], name.strip() or f"方案 {len(existing) + 1}",
                       float(cost), copy.deepcopy(ch)))
        self.refresh()

    def _remove(self, char_id: str, sc: qtc.Scheme) -> None:
        self.schemes[char_id] = [x for x in self.schemes.get(char_id, []) if x is not sc]
        if not self.schemes[char_id]:
            del self.schemes[char_id]
        self.refresh()

    def _start(self) -> None:
        if not self.s.enabled_chars:
            QMessageBox.information(self, "快速拉表", "没有启用的角色，无法拉表。")
            return
        self.accept()


class ProgressDialog(Modal):
    """计算进度。"""

    def __init__(self, parent, total: int):
        super().__init__(parent, "正在计算拉表组合", "loader-2", width=440, height=250)
        self.cancelled = False
        self.add(label("正在枚举所有角色方案组合并逐一结算……", "Copy", wrap=True))
        from PySide6.QtWidgets import QProgressBar
        self.bar = QProgressBar()
        self.bar.setRange(0, max(1, total))
        self.add(self.bar)
        self.info = label(f"已计算 0 / {total:,} 组", "Muted")
        self.add(self.info)
        self.finish_body()
        self.add_button("取消计算", "x", "", self._cancel)
        self.total = total

    def set_progress(self, done: int, total: int) -> None:
        self.bar.setRange(0, max(1, total))
        self.bar.setValue(done)
        self.info.setText(f"已计算 {done:,} / {total:,} 组（{done / max(1, total) * 100:.1f}%）")

    def _cancel(self) -> None:
        self.cancelled = True
        self.reject()


class ResultsDialog(Modal):
    """拉表结果表。"""

    def __init__(self, parent, session: Session, rows: List[qtc.QtResult],
                 char_info: List[Dict[str, str]]):
        super().__init__(parent, "快速拉表结果", "table", width=900, height=640)
        self.s = session
        self.all_rows = rows
        self.char_info = char_info
        self.pruned = False
        self.sort_field = "cost"
        self.cost_asc = True
        self.dmg_asc = False
        self.show_share = session.share_on

        bar = hbox(spacing=6)
        self.sort_cost = button("成本 ↑", "", "", self, self._sort_cost)
        self.sort_dmg = button("DPS ↓", "", "", self, self._sort_dmg)
        bar.addWidget(self.sort_cost)
        bar.addWidget(self.sort_dmg)
        self.prune_btn = button("", "", "", self, self._toggle_prune)
        bar.addWidget(self.prune_btn)
        if session.share_on:
            self.share_chip = chip("显示伤害占比", self, self._toggle_share, checkable=True)
            self.share_chip.setChecked(True)
            bar.addWidget(self.share_chip)
        bar.addStretch(1)
        self.summary = label("", "Muted")
        bar.addWidget(self.summary)
        self.body.addLayout(bar)

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.add(self.table, 1)

        self.add_button("导出 CSV", "file-down", "", self._export_csv)
        self.add_button("导出 Markdown", "clipboard-copy", "", self._export_md)
        self.add_button("关闭", "", "Primary", self.accept)
        self._apply_sort()

    # ------------------------------------------------------------------

    def _displayed(self) -> List[qtc.QtResult]:
        return qtc.prune_dominated(self.all_rows) if self.pruned else self.all_rows

    def _apply_sort(self) -> None:
        qtc.sort_results(self.all_rows, self.sort_field, self.cost_asc, self.dmg_asc)
        self.sort_cost.setText(f"成本 {'↑' if self.cost_asc else '↓'}")
        self.sort_dmg.setText(f"DPS {'↑' if self.dmg_asc else '↓'}")
        self.refresh()

    def refresh(self) -> None:
        rows = self._displayed()
        removed = len(self.all_rows) - len(rows)
        self.prune_btn.setText(f"恢复全部方案（已剔除 {removed}）" if self.pruned
                               else (f"剔除被偏序方案（{len(self.all_rows) - len(qtc.prune_dominated(self.all_rows))}）"
                                     if self.all_rows else "剔除被偏序方案"))
        extra = f" · 展示 {len(rows)} 个" if removed else ""
        self.summary.setText(f"共 {len(self.all_rows)} 种组合{extra} · 金色高亮 = 最高 DPS")

        has_reaction = qtc.has_reaction_column(self.all_rows)
        headers, body = qtc.build_table(rows, self.char_info, self.show_share, has_reaction)
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(body))
        best = max((r.dps for r in rows), default=0.0)
        dps_col = 1 + len(self.char_info)
        for i, (row, data) in enumerate(zip(rows, body)):
            for j, text in enumerate(data):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if j == dps_col and best > 0 and row.dps == best:
                    item.setForeground(QColor(theme.BLUE))
                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)
                self.table.setItem(i, j, item)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def _sort_cost(self) -> None:
        if self.sort_field == "cost":
            self.cost_asc = not self.cost_asc
        self.sort_field = "cost"
        self._apply_sort()

    def _sort_dmg(self) -> None:
        if self.sort_field == "dmg":
            self.dmg_asc = not self.dmg_asc
        self.sort_field = "dmg"
        self._apply_sort()

    def _toggle_prune(self) -> None:
        self.pruned = not self.pruned
        self.refresh()

    def _toggle_share(self) -> None:
        self.show_share = self.share_chip.isChecked()
        self.refresh()

    def _export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "导出 CSV", "quick-table.csv", "CSV (*.csv)")
        if path:
            qtc.write_csv(path, self._displayed(), self.char_info, self.show_share,
                          qtc.has_reaction_column(self.all_rows))

    def _export_md(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "导出 Markdown", "quick-table.md",
                                              "Markdown (*.md)")
        if path:
            qtc.write_markdown(path, self._displayed(), self.char_info, self.show_share,
                               qtc.has_reaction_column(self.all_rows))


def show_results(parent, session: Session, rows: List[qtc.QtResult],
                 char_info: List[Dict[str, str]]) -> None:
    if not rows:
        QMessageBox.information(parent, "快速拉表", "没有可显示的结果。")
        return
    ResultsDialog(parent, session, rows, char_info).exec()


def open_quick_table(parent, session: Session, editor) -> None:
    """完整流程：收集方案 → 后台计算 → 展示结果。"""
    if not session.enabled_chars:
        QMessageBox.information(parent, "快速拉表", "没有启用的角色，无法拉表。")
        return

    collector = SchemeCollector(parent, session, editor)
    if not collector.exec():
        return
    schemes = collector.schemes

    options = qtc.build_options(session.state, schemes)
    total = qtc.count_combinations(options)
    char_info = [{"id": c["id"], "name": str(c.get("name", ""))} for c in session.enabled_chars]

    progress = ProgressDialog(parent, total)
    worker = _Worker(copy.deepcopy(session.state), schemes)
    thread = QThread(parent)
    worker.moveToThread(thread)
    holder: Dict[str, Any] = {"rows": [], "error": ""}

    thread.started.connect(worker.run)
    worker.progress.connect(progress.set_progress)
    worker.done.connect(lambda rows: (holder.__setitem__("rows", rows), progress.accept()))
    worker.failed.connect(lambda msg: (holder.__setitem__("error", msg), progress.reject()))
    progress.rejected.connect(worker.cancel)
    thread.start()
    progress.exec()

    worker.cancel()
    thread.quit()
    thread.wait(5000)

    if holder["error"]:
        QMessageBox.warning(parent, "快速拉表失败", holder["error"])
        return
    rows = holder["rows"]
    if progress.cancelled and not rows:
        return
    if not rows:
        return

    session.storage.record_qt_history([r.to_json() for r in rows], char_info)
    show_results(parent, session, rows, char_info)
