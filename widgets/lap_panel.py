"""Lap times list — shown during/after a race when laps are recorded."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt

from qfluentwidgets import (
    PushButton, CardWidget, BodyLabel, SubtitleLabel, CaptionLabel,
    SmoothScrollArea, TransparentToolButton, FluentIcon as FIF, MessageBox,
)

from timer import format_time


class LapPanel(QWidget):
    """Displays recorded lap times in chronological order."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._laps: list[float] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        title = SubtitleLabel("Lap Times")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self._scroll = SmoothScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }")
        self._container = QWidget()
        self._container.setStyleSheet("QWidget { background: transparent; }")
        self._card_layout = QVBoxLayout(self._container)
        self._card_layout.setAlignment(Qt.AlignTop)
        self._card_layout.setSpacing(4)
        self._scroll.setWidget(self._container)
        layout.addWidget(self._scroll, 1)

        clear_btn = PushButton("Clear Laps")
        clear_btn.setMinimumHeight(32)
        clear_btn.clicked.connect(self._confirm_clear)
        layout.addWidget(clear_btn)

    @property
    def laps(self) -> list[float]:
        return self._laps

    def add_lap(self, race_ms: float):
        self._laps.append(race_ms)
        self._refresh()

    def clear(self):
        self._laps.clear()
        self._refresh()

    def _confirm_clear(self):
        if not self._laps:
            return
        msg = MessageBox("Confirm", "Clear all lap times?", self.window())
        if msg.exec():
            self.clear()

    def _refresh(self):
        while self._card_layout.count():
            item = self._card_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for i, ms in enumerate(self._laps):
            self._card_layout.addWidget(self._make_card(i, ms))

    def _make_card(self, index: int, ms: float) -> CardWidget:
        card = CardWidget()
        lay = QHBoxLayout(card)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(6)

        idx_label = CaptionLabel(f"Lap {index + 1}")
        lay.addWidget(idx_label)

        time_label = BodyLabel(format_time(ms))
        time_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        time_label.setAlignment(Qt.AlignCenter)
        lay.addWidget(time_label, 1)

        del_btn = TransparentToolButton(FIF.DELETE)
        del_btn.setFixedSize(28, 28)
        del_btn.clicked.connect(lambda _, idx=index: self._delete(idx))
        lay.addWidget(del_btn)

        return card

    def _delete(self, index: int):
        if 0 <= index < len(self._laps):
            self._laps.pop(index)
            self._refresh()
