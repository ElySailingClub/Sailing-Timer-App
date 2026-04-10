"""Right panel — finish times list with racer linking, lap tracking, corrected times."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QDialog, QFormLayout, QSpinBox,
)
from PySide6.QtCore import Qt, Signal

from qfluentwidgets import (
    PushButton, PrimaryPushButton, ComboBox, CardWidget, BodyLabel,
    SubtitleLabel, CaptionLabel, SmoothScrollArea, MessageBox,
    TransparentToolButton, FluentIcon as FIF,
)

from timer import format_time
from boat_handicaps import get_handicap


class EditTimeDialog(QDialog):
    """Simple dialog to edit a finish time (HH:MM:SS)."""

    def __init__(self, current_ms: float, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Finish Time")
        self.setFixedSize(280, 180)
        self.setModal(True)

        total_sec = abs(int(current_ms)) // 1000
        h = total_sec // 3600
        m = (total_sec % 3600) // 60
        s = total_sec % 60

        form = QFormLayout(self)
        form.setSpacing(10)
        form.setContentsMargins(20, 20, 20, 20)

        self._h = QSpinBox()
        self._h.setRange(0, 23)
        self._h.setValue(h)
        form.addRow("Hours:", self._h)

        self._m = QSpinBox()
        self._m.setRange(0, 59)
        self._m.setValue(m)
        form.addRow("Minutes:", self._m)

        self._s = QSpinBox()
        self._s.setRange(0, 59)
        self._s.setValue(s)
        form.addRow("Seconds:", self._s)

        btn_row = QHBoxLayout()
        save_btn = PrimaryPushButton("Save")
        save_btn.clicked.connect(self.accept)
        cancel_btn = PushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        form.addRow(btn_row)

    def get_ms(self) -> float:
        return (self._h.value() * 3600 + self._m.value() * 60 + self._s.value()) * 1000


class FinishPanel(QWidget):
    dnf_clicked = Signal()
    dns_clicked = Signal()
    data_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: list[dict] = []
        self._participants: list[dict] = []
        self._total_laps: int | None = None
        self._refreshing = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        title = SubtitleLabel("Finishing Times")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self._scroll = SmoothScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self._container = QWidget()
        self._container.setStyleSheet("QWidget { background: transparent; }")
        self._card_layout = QVBoxLayout(self._container)
        self._card_layout.setAlignment(Qt.AlignTop)
        self._card_layout.setSpacing(4)
        self._scroll.setWidget(self._container)
        layout.addWidget(self._scroll, 1)

        btn_row = QHBoxLayout()
        dnf_btn = PushButton("Add DNF")
        dnf_btn.setMinimumHeight(36)
        dnf_btn.clicked.connect(self.dnf_clicked.emit)
        btn_row.addWidget(dnf_btn)

        dns_btn = PushButton("Add DNS")
        dns_btn.setMinimumHeight(36)
        dns_btn.clicked.connect(self.dns_clicked.emit)
        btn_row.addWidget(dns_btn)
        layout.addLayout(btn_row)

    # ── Public ──────────────────────────────────────────────────────────

    @property
    def entries(self) -> list[dict]:
        return self._entries

    def add_entry(self, entry: dict):
        self._entries.append(entry)
        self._refresh()
        self.data_changed.emit()

    def clear(self):
        self._entries.clear()
        self._refresh()

    def set_participants(self, participants: list[dict]):
        self._participants = participants
        self._refresh()

    def set_total_laps(self, laps: int | None):
        self._total_laps = laps
        self._refresh()

    # ── Position / corrected time computation ───────────────────────────

    def _compute_positions(self):
        """Compute corrected times and positions for all linked entries."""
        total_laps = self._total_laps or 1
        scored = []

        for entry in self._entries:
            if entry.get("racerid") and entry["finishTime"] > 0:
                racer = next(
                    (r for r in self._participants if r["id"] == entry["racerid"]),
                    None,
                )
                if racer:
                    py = get_handicap(racer["boatClass"])
                    if py:
                        laps = entry.get("lapsCompleted") or total_laps
                        corrected = (entry["finishTime"] / laps) * total_laps * 1000 / py
                        entry["_correctedMs"] = corrected
                        entry["_correctedStr"] = format_time(corrected)
                        scored.append(entry)
                        continue

            entry["_correctedMs"] = None
            entry["_correctedStr"] = None
            entry["_position"] = None

        scored.sort(key=lambda e: e["_correctedMs"])
        for i, e in enumerate(scored):
            e["_position"] = i + 1

    # ── UI rebuild ──────────────────────────────────────────────────────

    def _refresh(self):
        if self._refreshing:
            return
        self._refreshing = True
        try:
            self._compute_positions()
            while self._card_layout.count():
                item = self._card_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            for i, entry in enumerate(self._entries):
                self._card_layout.addWidget(self._make_card(entry, i))
        finally:
            self._refreshing = False

    def _make_card(self, entry: dict, index: int) -> CardWidget:
        card = CardWidget()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(2)

        # Top row: buttons
        top = QHBoxLayout()
        top.addStretch()

        if entry["finishTime"] > 0:
            edit_btn = TransparentToolButton(FIF.EDIT)
            edit_btn.setFixedSize(28, 28)
            edit_btn.clicked.connect(lambda _, idx=index: self._edit_time(idx))
            top.addWidget(edit_btn)

        del_btn = TransparentToolButton(FIF.DELETE)
        del_btn.setFixedSize(28, 28)
        del_btn.clicked.connect(lambda _, idx=index: self._delete(idx))
        top.addWidget(del_btn)
        lay.addLayout(top)

        # Time display
        if entry["finishTime"] == -1:
            time_text = "DNF"
        elif entry["finishTime"] == -2:
            time_text = "DNS"
        else:
            time_text = format_time(entry["finishTime"])
        time_label = BodyLabel(time_text)
        time_label.setAlignment(Qt.AlignCenter)
        time_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        lay.addWidget(time_label)

        # Corrected time + position (if available)
        pos = entry.get("_position")
        corr = entry.get("_correctedStr")
        if pos is not None and corr is not None:
            pos_label = CaptionLabel(f"Corrected: {corr}  |  Pos: {pos}")
            pos_label.setAlignment(Qt.AlignCenter)
            lay.addWidget(pos_label)

        # Laps dropdown (non-DNF/DNS only)
        if entry.get("lapsCompleted") is not None:
            lap_row = QHBoxLayout()
            lap_row.addWidget(CaptionLabel("Laps:"))
            lap_combo = ComboBox()
            lap_combo.addItems([str(j) for j in range(1, 9)])
            current = entry["lapsCompleted"] or 1
            lap_combo.setCurrentIndex(max(0, current - 1))
            lap_combo.currentIndexChanged.connect(
                lambda idx, e=entry: self._on_laps_change(e, idx))
            lap_row.addWidget(lap_combo)
            lay.addLayout(lap_row)

        # Racer link dropdown
        link = ComboBox()
        link_ids = [None] + [r["id"] for r in self._participants]
        link.addItems(
            ["(unlinked)"] +
            [f"#{r['sailNo']} {r['helm']}" for r in self._participants]
        )
        if entry.get("racerid") is not None:
            for j, rid in enumerate(link_ids):
                if rid == entry["racerid"]:
                    link.setCurrentIndex(j)
                    break
        link.currentIndexChanged.connect(
            lambda idx, ids=link_ids, e=entry: self._on_link_change(e, ids, idx))
        lay.addWidget(link)

        return card

    # ── Data change handlers ────────────────────────────────────────────

    def _on_link_change(self, entry, link_ids, idx):
        entry["racerid"] = link_ids[idx] if idx < len(link_ids) else None
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self._refresh)
        self.data_changed.emit()

    def _on_laps_change(self, entry, idx):
        entry["lapsCompleted"] = idx + 1
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self._refresh)
        self.data_changed.emit()

    def _edit_time(self, index: int):
        entry = self._entries[index]
        dlg = EditTimeDialog(entry["finishTime"], self.window())
        if dlg.exec() == QDialog.Accepted:
            entry["finishTime"] = dlg.get_ms()
            self._refresh()
            self.data_changed.emit()

    def _delete(self, index: int):
        msg = MessageBox("Confirm", "Delete this finish time?", self.window())
        if msg.exec():
            self._entries.pop(index)
            self._refresh()
            self.data_changed.emit()
