"""Centre panel — timer display, race controls, and action buttons."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal

from qfluentwidgets import (
    PushButton, PrimaryPushButton, ComboBox,
    BodyLabel, SubtitleLabel,
)


class TimerPanel(QWidget):
    start_clicked = Signal()
    stop_clicked = Signal()
    reset_clicked = Signal()
    store_clicked = Signal()
    race_type_changed = Signal(str)
    print_results_clicked = Signal()
    print_starts_clicked = Signal()
    export_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)

        # ── Controls row ────────────────────────────────────────────────
        ctrl = QHBoxLayout()

        ctrl.addWidget(BodyLabel("Race type:"))
        self._race_type = ComboBox()
        self._race_types = ["handicap", "pursuit", "counter"]
        self._race_type.addItems(["5, 4, 1, Go", "Pursuit", "Counter"])
        self._race_type.currentIndexChanged.connect(
            lambda: self.race_type_changed.emit(self.race_type))
        ctrl.addWidget(self._race_type)

        ctrl.addWidget(BodyLabel("Laps:"))
        self._laps = ComboBox()
        self._laps.addItems(["—"] + [str(i) for i in range(1, 9)])
        ctrl.addWidget(self._laps)

        self._racer_count = BodyLabel("Racers: 0")
        ctrl.addWidget(self._racer_count)
        ctrl.addStretch()
        layout.addLayout(ctrl)

        # ── Timer display ───────────────────────────────────────────────
        self._display = QLabel("00.05.10")
        self._display.setAlignment(Qt.AlignCenter)
        self._display.setStyleSheet("""
            QLabel {
                font-size: 80px;
                font-weight: bold;
                background-color: rgba(255, 192, 219, 0.8);
                border: 2px solid rgba(10, 7, 42, 60);
                border-radius: 16px;
                padding: 10px 40px;
            }
        """)
        layout.addWidget(self._display)

        # ── Action buttons ──────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self._start_btn = PrimaryPushButton("START")
        self._start_btn.setMinimumWidth(100)
        self._start_btn.setMinimumHeight(40)
        self._start_btn.clicked.connect(self._on_start_stop_clicked)
        btn_row.addWidget(self._start_btn)
        self._timer_running = False

        for text, signal in [
            ("RESET", self.reset_clicked),
            ("STORE", self.store_clicked),
        ]:
            btn = PushButton(text)
            btn.setMinimumWidth(100)
            btn.setMinimumHeight(40)
            btn.clicked.connect(signal.emit)
            btn_row.addWidget(btn)
        layout.addLayout(btn_row)

        # ── Print / export row (hidden by default) ──────────────────────
        self._end_row = QWidget()
        er = QHBoxLayout(self._end_row)
        er.setContentsMargins(0, 8, 0, 0)

        self._print_results_btn = PushButton("Print Results")
        self._print_results_btn.clicked.connect(self.print_results_clicked.emit)
        er.addWidget(self._print_results_btn)

        self._print_starts_btn = PushButton("Print Start Times")
        self._print_starts_btn.clicked.connect(self.print_starts_clicked.emit)
        er.addWidget(self._print_starts_btn)

        self._export_btn = PushButton("Export CSV")
        self._export_btn.clicked.connect(self.export_clicked.emit)
        er.addWidget(self._export_btn)

        self._end_row.hide()
        layout.addWidget(self._end_row)
        layout.addStretch()

    # ── Public interface ────────────────────────────────────────────────

    @property
    def race_type(self) -> str:
        idx = self._race_type.currentIndex()
        return self._race_types[idx] if 0 <= idx < len(self._race_types) else "handicap"

    @property
    def total_laps(self) -> int | None:
        idx = self._laps.currentIndex()
        return idx if idx >= 1 else None

    def set_display(self, text: str):
        self._display.setText(text)

    def set_racer_count(self, n: int):
        self._racer_count.setText(f"Racers: {n}")

    def set_controls_enabled(self, enabled: bool):
        self._race_type.setEnabled(enabled)

    def show_end_buttons(self, race_type: str):
        self._end_row.show()
        self._print_results_btn.setVisible(race_type == "handicap")
        self._print_starts_btn.setVisible(race_type == "pursuit")
        self._export_btn.setVisible(race_type == "handicap")

    def hide_end_buttons(self):
        self._end_row.hide()

    def set_timer_running(self, running: bool):
        """Update the start/stop button to reflect the timer state."""
        self._timer_running = running
        self._start_btn.setText("END" if running else "START")

    def _on_start_stop_clicked(self):
        if self._timer_running:
            self.stop_clicked.emit()
        else:
            self.start_clicked.emit()
