"""Race timer state machine — handles countdown and race elapsed timing."""

import time
from PySide6.QtCore import QObject, Signal


def format_time(ms: float) -> str:
    """Format milliseconds as HH.MM.SS (absolute value)."""
    total_sec = abs(int(ms)) // 1000
    h = total_sec // 3600
    m = (total_sec % 3600) // 60
    s = total_sec % 60
    return f"{h:02d}.{m:02d}.{s:02d}"


class RaceTimer(QObject):
    """Counts down from the start sequence, then counts up for race elapsed time.

    ``current_ms`` is positive during countdown and negative once the race is
    underway (so ``race_elapsed_ms`` = ``abs(current_ms)`` when negative).
    """

    alert_fired = Signal()
    auto_stopped = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timing = False
        self._race_type = "handicap"
        self._saved_ms = 310_000.0
        self._current_ms = 310_000.0
        self._start_epoch = 0.0
        self._alerts: list[list] = []

    # ── Properties ──────────────────────────────────────────────────────

    @property
    def timing(self) -> bool:
        return self._timing

    @property
    def current_ms(self) -> float:
        return self._current_ms

    @property
    def race_elapsed_ms(self) -> float:
        return abs(self._current_ms) if self._current_ms < 0 else 0

    @property
    def display_text(self) -> str:
        return format_time(self._current_ms)

    # ── Controls ────────────────────────────────────────────────────────

    def reset(self, race_type: str, boats: list[tuple[int, str]] | None = None):
        self._timing = False
        self._race_type = race_type
        self._saved_ms = 310_000.0 if race_type in ("handicap", "pursuit") else 10_000.0
        self._current_ms = self._saved_ms
        self._build_alerts(boats or [])

    def start(self):
        if not self._timing:
            self._start_epoch = time.time()
            self._timing = True

    def stop(self):
        if self._timing:
            elapsed = (time.time() - self._start_epoch) * 1000
            self._saved_ms -= elapsed
            self._current_ms = self._saved_ms
            self._timing = False

    def tick(self) -> bool:
        """Call every frame. Returns True if any alert triggered."""
        if not self._timing:
            return False

        elapsed = (time.time() - self._start_epoch) * 1000
        self._current_ms = self._saved_ms - elapsed

        triggered = False
        for alert in self._alerts:
            if not alert[1] and self._current_ms <= alert[0]:
                alert[1] = True
                triggered = True

        if self._race_type == "pursuit" and self._current_ms < -2_700_000:
            self.stop()
            self.auto_stopped.emit()
            triggered = True

        if triggered:
            self.alert_fired.emit()
        return triggered

    # ── Internal ────────────────────────────────────────────────────────

    def _build_alerts(self, boats: list[tuple[int, str]]):
        if self._race_type in ("handicap", "pursuit"):
            # Added hacky fix by increcing these by 1
            self._alerts = [
                [301_000, False],   # 5:00 horn
                [241_000, False],   # 4:00 horn
                [61_000,  False],   # 1:00 horn
                [1_000,       False],   # GO   horn
            ]
        else:
            self._alerts = [[0, False]]

        if self._race_type == "pursuit" and len(boats) > 1:
            for i in range(1, len(boats)):
                offset = ((boats[0][0] - boats[i][0]) / boats[0][0]) * 2_700_000
                self._alerts.append([-offset, False])
