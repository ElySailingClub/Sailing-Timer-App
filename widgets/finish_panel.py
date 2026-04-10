"""Right panel — finish times list with racer linking and lap tracking."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt, Signal

from qfluentwidgets import (
    PushButton, ComboBox, CardWidget, BodyLabel, SubtitleLabel,
    CaptionLabel, SmoothScrollArea, MessageBox,
)

from timer import format_time


class FinishPanel(QWidget):
    dnf_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: list[dict] = []
        self._participants: list[dict] = []

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
        self._card_layout.setSpacing(6)
        self._scroll.setWidget(self._container)
        layout.addWidget(self._scroll, 1)

        dnf_btn = PushButton("Add DNF")
        dnf_btn.setMinimumHeight(40)
        dnf_btn.clicked.connect(self.dnf_clicked.emit)
        layout.addWidget(dnf_btn)

    # ── Public ──────────────────────────────────────────────────────────

    @property
    def entries(self) -> list[dict]:
        return self._entries

    def add_entry(self, entry: dict):
        self._entries.insert(0, entry)
        self._refresh()

    def clear(self):
        self._entries.clear()
        self._refresh()

    def set_participants(self, participants: list[dict]):
        self._participants = participants
        self._refresh()

    # ── UI rebuild ──────────────────────────────────────────────────────

    def _refresh(self):
        while self._card_layout.count():
            item = self._card_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for i, entry in enumerate(self._entries):
            self._card_layout.addWidget(self._make_card(entry, i))

    def _make_card(self, entry: dict, index: int) -> CardWidget:
        card = CardWidget()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(4)

        # Delete button row
        top = QHBoxLayout()
        top.addStretch()
        del_btn = PushButton("×")
        del_btn.setFixedSize(30, 30)
        del_btn.clicked.connect(lambda _, idx=index: self._delete(idx))
        top.addWidget(del_btn)
        lay.addLayout(top)

        # Time display
        if entry["finishTime"] == -1:
            time_label = BodyLabel("DNF")
        else:
            time_label = BodyLabel(format_time(entry["finishTime"]))
        time_label.setAlignment(Qt.AlignCenter)
        time_label.setStyleSheet("font-size: 22px; font-weight: bold;")
        lay.addWidget(time_label)

        # Laps dropdown (non-DNF only)
        if entry.get("lapsCompleted") is not None:
            lap_row = QHBoxLayout()
            lap_row.addWidget(CaptionLabel("Laps:"))
            lap_combo = ComboBox()
            lap_combo.addItems([str(j) for j in range(1, 9)])
            current = entry["lapsCompleted"] or 1
            lap_combo.setCurrentIndex(max(0, current - 1))
            lap_combo.currentIndexChanged.connect(
                lambda idx, e=entry: e.__setitem__("lapsCompleted", idx + 1))
            lap_row.addWidget(lap_combo)
            lay.addLayout(lap_row)

        # Racer link dropdown
        link = ComboBox()
        link_ids = [None] + [r["id"] for r in self._participants]
        link.addItems(["(unlinked)"] + [f"{r['helm']} – {r['sailNo']}" for r in self._participants])
        if entry.get("racerid") is not None:
            for j, rid in enumerate(link_ids):
                if rid == entry["racerid"]:
                    link.setCurrentIndex(j)
                    break
        link.currentIndexChanged.connect(
            lambda idx, ids=link_ids, e=entry: e.__setitem__("racerid", ids[idx] if idx < len(ids) else None))
        lay.addWidget(link)

        return card

    def _delete(self, index: int):
        msg = MessageBox("Confirm", "Delete this finish time?", self.window())
        if msg.exec():
            self._entries.pop(index)
            self._refresh()
