"""Main application window — assembles panels and wires signals."""

import csv
import sys

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget, QLabel, QFileDialog
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QTextDocument
from PySide6.QtPrintSupport import QPrinter, QPrintDialog

from qfluentwidgets import (
    PushButton, ComboBox, BodyLabel,
    MessageBox, InfoBar, InfoBarPosition,
    setTheme, Theme, setThemeColor, isDarkTheme,
)

try:
    from qframelesswindow import AcrylicWindow as _WindowBase
except Exception:
    from PySide6.QtWidgets import QWidget as _WindowBase

import data
from boat_handicaps import get_handicap, display_name
from timer import RaceTimer, format_time
from serial_handler import SerialHandler
from widgets import RacerPanel, TimerPanel, FinishPanel


class MainWindow(_WindowBase):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ESC Race Box — Sailing Timer")
        self.resize(1280, 780)

        # Acrylic / Mica tint (if AcrylicWindow)
        if hasattr(self, "windowEffect"):
            try:
                if isDarkTheme():
                    self.windowEffect.setAcrylicEffect(
                        self.winId(), gradientColor="F0202020")
                else:
                    self.windowEffect.setAcrylicEffect(
                        self.winId(), gradientColor="F5EFF2F0")
            except Exception:
                pass

        # Fallback background for dark mode (when acrylic isn't supported)
        if isDarkTheme():
            self.setStyleSheet("MainWindow { background-color: #202020; }")

        # Fix title bar button colors for dark mode
        if isDarkTheme() and hasattr(self, "titleBar"):
            for btn in (self.titleBar.minBtn, self.titleBar.maxBtn, self.titleBar.closeBtn):
                btn.setNormalColor(QColor("white"))
                btn.setHoverColor(QColor("white"))
                btn.setPressedColor(QColor("white"))

        # ── Data ────────────────────────────────────────────────────────
        self._data = data.load()
        self._participants: list[dict] = []
        self._boats: list[tuple[int, str]] = []
        self._time_id = 1

        # ── Timer & serial ──────────────────────────────────────────────
        self._timer = RaceTimer(self)
        self._serial = SerialHandler(self)

        # ── Build UI ────────────────────────────────────────────────────
        self._build_ui()
        self._wire_signals()

        # ── Tick (20 fps) ───────────────────────────────────────────────
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start(50)

        self._reset_timer()

    # ════════════════════════════════════════════════════════════════════
    #  UI BUILD
    # ════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        # Account for the title bar in frameless windows
        tb_h = self.titleBar.height() if hasattr(self, "titleBar") else 0
        root_layout.setContentsMargins(10, tb_h + 8, 10, 10)

        # ── Serial connection bar ───────────────────────────────────────
        serial_bar = QHBoxLayout()
        serial_bar.addWidget(BodyLabel("Port:"))

        self._port_combo = ComboBox()
        self._port_combo.setMinimumWidth(130)
        self._refresh_ports()
        serial_bar.addWidget(self._port_combo)

        refresh_btn = PushButton("↻")
        refresh_btn.setFixedWidth(36)
        refresh_btn.clicked.connect(self._refresh_ports)
        serial_bar.addWidget(refresh_btn)

        self._connect_btn = PushButton("Connect")
        self._connect_btn.clicked.connect(self._toggle_serial)
        serial_bar.addWidget(self._connect_btn)

        self._conn_label = BodyLabel("Disconnected")
        self._conn_label.setStyleSheet("color: #C42B1C; font-weight: bold;")
        serial_bar.addWidget(self._conn_label)
        serial_bar.addStretch()
        root_layout.addLayout(serial_bar)

        # ── Three-column content ────────────────────────────────────────
        columns = QHBoxLayout()
        columns.setSpacing(14)

        self._racer_panel = RacerPanel(self._data, self)
        self._timer_panel = TimerPanel(self)
        self._finish_panel = FinishPanel(self)

        columns.addWidget(self._racer_panel, 1)
        columns.addWidget(self._timer_panel, 2)
        columns.addWidget(self._finish_panel, 1)
        root_layout.addLayout(columns)

    # ════════════════════════════════════════════════════════════════════
    #  SIGNAL WIRING
    # ════════════════════════════════════════════════════════════════════

    def _wire_signals(self):
        tp = self._timer_panel
        tp.start_clicked.connect(self._start_timer)
        tp.stop_clicked.connect(self._stop_timer)
        tp.reset_clicked.connect(self._reset_confirm)
        tp.store_clicked.connect(self._store_time)
        tp.race_type_changed.connect(self._on_race_type_change)
        tp.print_results_clicked.connect(self._print_results)
        tp.print_starts_clicked.connect(self._print_starts)
        tp.export_clicked.connect(self._export_csv)

        self._racer_panel.participation_changed.connect(
            self._on_participation_changed)
        self._finish_panel.dnf_clicked.connect(lambda: self._store_time(dnf=True))
        self._finish_panel.dns_clicked.connect(lambda: self._store_time(dns=True))
        self._finish_panel.data_changed.connect(self._update_counts)

        self._serial.packet_received.connect(self._on_serial_packet)
        self._serial.connection_changed.connect(self._on_connection_changed)
        self._timer.alert_fired.connect(self._send_horn)
        self._timer.auto_stopped.connect(self._on_auto_stop)

    # ════════════════════════════════════════════════════════════════════
    #  SERIAL
    # ════════════════════════════════════════════════════════════════════

    def _refresh_ports(self):
        self._port_combo.clear()
        ports = SerialHandler.available_ports()
        if ports:
            self._port_combo.addItems(ports)
        else:
            self._port_combo.addItem("No ports")

    def _toggle_serial(self):
        if self._serial.is_connected:
            self._serial.disconnect_port()
        else:
            port = self._port_combo.currentText()
            if port and port != "No ports":
                self._serial.connect_port(port)

    def _on_connection_changed(self, connected: bool):
        if connected:
            self._conn_label.setText("Connected")
            self._conn_label.setStyleSheet("color: #0F7B0F; font-weight: bold;")
            self._connect_btn.setText("Disconnect")
        else:
            self._conn_label.setText("Disconnected")
            self._conn_label.setStyleSheet("color: #C42B1C; font-weight: bold;")
            self._connect_btn.setText("Connect")

    def _on_serial_packet(self, packet: dict):
        ptype = packet.get("packet-type")
        if ptype == "button-input":
            btn = packet.get("button")
            if btn == "store":
                self._serial.send_sound("beep")
                self._store_time()
            elif btn == "recall":
                self._serial.send_sound("horn")
            elif btn == "shortened":
                self._serial.send_sound("shortened")
        elif ptype == "log":
            level = packet.get("type", "info")
            msg = packet.get("message", "")
            print(f"[RaceBox {level.upper()}] {msg}")

    def _send_horn(self):
        self._serial.send_sound("horn")

    # ════════════════════════════════════════════════════════════════════
    #  TIMER
    # ════════════════════════════════════════════════════════════════════

    def _reset_timer(self):
        rtype = self._timer_panel.race_type
        self._timer.reset(rtype, self._boats)
        self._timer_panel.set_display(self._timer.display_text)
        self._timer_panel.hide_end_buttons()
        self._finish_panel.clear()
        self._time_id = 1
        self._racer_panel.set_editable(True)
        self._timer_panel.set_controls_enabled(True)
        self._timer_panel.set_timer_running(False)

    def _reset_confirm(self):
        if self._timer.timing:
            self._show_warning("Cannot reset while the timer is running.")
            return
        msg = MessageBox("Confirm", "Reset the timer?", self)
        if msg.exec():
            self._reset_timer()

    def _start_timer(self):
        if self._timer.timing:
            return
        rtype = self._timer_panel.race_type
        if rtype != "counter" and self._timer_panel.total_laps is None:
            self._show_warning("Please select a number of laps.")
            return
        self._timer.start()
        self._racer_panel.set_editable(False)
        self._timer_panel.set_controls_enabled(False)
        self._timer_panel.set_timer_running(True)

    def _stop_timer(self):
        if not self._timer.timing:
            self._show_warning("Timer has not started.")
            return
        msg = MessageBox("Confirm", "End the race?", self)
        if msg.exec():
            self._do_stop()

    def _do_stop(self):
        self._timer.stop()
        self._timer_panel.set_display(self._timer.display_text)
        self._timer_panel.set_controls_enabled(True)
        self._timer_panel.set_timer_running(False)
        self._timer_panel.show_end_buttons(self._timer_panel.race_type)

    def _on_auto_stop(self):
        self._timer_panel.set_display(self._timer.display_text)
        self._timer_panel.set_controls_enabled(True)
        self._timer_panel.set_timer_running(False)
        self._timer_panel.show_end_buttons("pursuit")

    def _tick(self):
        triggered = self._timer.tick()
        if self._timer.timing:
            self._timer_panel.set_display(self._timer.display_text)

    # ════════════════════════════════════════════════════════════════════
    #  PARTICIPATION
    # ════════════════════════════════════════════════════════════════════

    def _on_participation_changed(self, participants: list[dict]):
        self._participants = participants
        self._update_boats()
        self._finish_panel.set_participants(participants)
        self._finish_panel.set_total_laps(self._timer_panel.total_laps)
        self._update_counts()

    def _update_boats(self):
        seen = set()
        boats = []
        for r in self._participants:
            h = get_handicap(r["boatClass"])
            if h and r["boatClass"] not in seen:
                seen.add(r["boatClass"])
                boats.append((h, r["boatClass"]))
        boats.sort(reverse=True)
        self._boats = boats
        if not self._timer.timing:
            self._timer.reset(self._timer_panel.race_type, self._boats)
            self._timer_panel.set_display(self._timer.display_text)

    def _on_race_type_change(self, _rtype: str):
        if not self._timer.timing:
            self._reset_timer()

    def _update_counts(self):
        n_entries = len(self._participants)
        n_finished = sum(
            1 for e in self._finish_panel.entries if e["finishTime"] > 0
        )
        self._timer_panel.set_counts(n_entries, n_finished)

    # ════════════════════════════════════════════════════════════════════
    #  FINISH TIMES
    # ════════════════════════════════════════════════════════════════════

    def _store_time(self, dnf=False, dns=False):
        rtype = self._timer_panel.race_type
        if rtype == "pursuit":
            return
        if not dnf and not dns:
            if not self._timer.timing:
                self._show_warning("Timer has not started.")
                return
            race_ms = self._timer.race_elapsed_ms
            if race_ms <= 0:
                self._show_warning("Race hasn't started yet (still in countdown).")
                return
            entry = {
                "id": self._time_id,
                "finishTime": race_ms,
                "lapsCompleted": self._timer_panel.total_laps,
                "racerid": None,
            }
        elif dns:
            entry = {
                "id": self._time_id,
                "finishTime": -2,
                "lapsCompleted": None,
                "racerid": None,
            }
        else:
            entry = {
                "id": self._time_id,
                "finishTime": -1,
                "lapsCompleted": None,
                "racerid": None,
            }
        self._time_id += 1
        self._finish_panel.set_total_laps(self._timer_panel.total_laps)
        self._finish_panel.add_entry(entry)
        self._update_counts()

    # ════════════════════════════════════════════════════════════════════
    #  RESULTS & EXPORT
    # ════════════════════════════════════════════════════════════════════

    def _compute_results(self) -> list[dict]:
        total_laps = self._timer_panel.total_laps or 1
        entries = self._finish_panel.entries
        results = []
        for r in self._participants:
            row = dict(r)
            ft = next((e for e in entries if e.get("racerid") == r["id"]), None)
            if ft and ft["finishTime"] > 0:
                laps = ft.get("lapsCompleted") or total_laps
                row["laps"] = laps
                row["finishTimeStr"] = format_time(ft["finishTime"])
                py = get_handicap(r["boatClass"])
                if py and laps:
                    corrected = (ft["finishTime"] / laps) * total_laps * 1000 / py
                    row["correctedMs"] = corrected
                    row["correctedStr"] = format_time(corrected)
                else:
                    row["correctedMs"] = float("inf")
                    row["correctedStr"] = "N/A"
            elif ft and ft["finishTime"] == -2:
                row["laps"] = "DNS"
                row["finishTimeStr"] = "DNS"
                row["correctedMs"] = float("inf")
                row["correctedStr"] = "DNS"
            else:
                row["laps"] = "DNF"
                row["finishTimeStr"] = "DNF"
                row["correctedMs"] = float("inf")
                row["correctedStr"] = "DNF"
            results.append(row)
        results.sort(key=lambda x: x["correctedMs"])
        return results

    def _print_results(self):
        if not self._participants:
            self._show_warning("No racers selected.")
            return
        results = self._compute_results()
        html = self._results_html(results)
        self._print_html(html)

    def _print_starts(self):
        if not self._participants or not self._boats:
            self._show_warning("No racers selected.")
            return
        html = self._starts_html()
        self._print_html(html)

    def _export_csv(self):
        if not self._participants:
            self._show_warning("No racers selected.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Results", "race_results.csv", "CSV Files (*.csv)")
        if not path:
            return
        results = self._compute_results()
        officer = self._timer_panel.officer
        race_date = self._timer_panel.race_date
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            if officer or race_date:
                writer.writerow([f"Race Officer: {officer}", f"Date: {race_date}"])
                writer.writerow([])
            writer.writerow([
                "Position", "Helm", "Crew", "Boat Class",
                "Sail Number", "Laps", "Finish Time", "Corrected Time",
            ])
            for i, r in enumerate(results):
                writer.writerow([
                    i + 1, r["helm"], r["crew"], r["boatClass"],
                    r["sailNo"], r["laps"], r["finishTimeStr"],
                    r["correctedStr"],
                ])
        InfoBar.success(
            title="Exported",
            content=f"Results saved to {path}",
            parent=self,
            position=InfoBarPosition.TOP_RIGHT,
            duration=3000,
        )

    # ── HTML helpers ────────────────────────────────────────────────────

    def _race_info_html(self) -> str:
        officer = self._timer_panel.officer
        race_date = self._timer_panel.race_date
        parts = []
        if officer:
            parts.append(f"Race Officer: {officer}")
        if race_date:
            parts.append(f"Date: {race_date}")
        if parts:
            return f"<p style='text-align:center'>{' &nbsp;|&nbsp; '.join(parts)}</p>"
        return ""

    def _results_html(self, results: list[dict]) -> str:
        rows = ""
        for i, r in enumerate(results):
            rows += (
                f"<tr><td>{i+1}</td><td>{r['helm']}</td><td>{r['crew']}</td>"
                f"<td>{display_name(r['boatClass'])}</td><td>{r['sailNo']}</td>"
                f"<td>{r['laps']}</td><td>{r['finishTimeStr']}</td>"
                f"<td>{r['correctedStr']}</td></tr>"
            )
        return (
            "<h2 style='text-align:center'>Race Results</h2>"
            f"{self._race_info_html()}"
            "<table border='1' cellpadding='6' cellspacing='0'"
            " style='border-collapse:collapse;width:100%'>"
            "<tr><th>Pos</th><th>Helm</th><th>Crew</th><th>Boat</th>"
            "<th>Sail</th><th>Laps</th><th>Finish</th><th>Corrected</th></tr>"
            f"{rows}</table>"
        )

    def _starts_html(self) -> str:
        rtype = self._timer_panel.race_type
        total_laps = self._timer_panel.total_laps or 1
        info = self._race_info_html()

        if rtype == "pursuit":
            boats = self._boats
            boat_rows = ""
            for i, (handicap, name) in enumerate(boats):
                offset = (
                    0 if i == 0
                    else ((boats[0][0] - handicap) / boats[0][0]) * 2_700_000
                )
                boat_rows += f"<tr><td>{format_time(offset)}</td><td>{display_name(name)}</td></tr>"
            racer_rows = "".join(
                f"<tr><td>#{r['sailNo']} {r['helm']}</td><td></td></tr>"
                for r in self._participants
            )
            return (
                f"<h2 style='text-align:center'>Pursuit Start Times</h2>{info}"
                "<table border='1' cellpadding='6' cellspacing='0'"
                " style='border-collapse:collapse;width:80%;margin:auto'>"
                f"<tr><th>Start Time</th><th>Boat Class</th></tr>{boat_rows}</table>"
                "<br>"
                "<table border='1' cellpadding='6' cellspacing='0'"
                " style='border-collapse:collapse;width:60%;margin:auto'>"
                f"<tr><th>Racer</th><th>Place</th></tr>{racer_rows}</table>"
            )
        else:
            lap_cols = "".join(f"<th>Lap {i+1}</th>" for i in range(total_laps))
            rows = ""
            for r in self._participants:
                empty = "<td>&nbsp;</td>" * total_laps
                rows += (
                    f"<tr><td>{r['sailNo']}</td><td>{r['helm']}</td>"
                    f"<td>{display_name(r['boatClass'])}</td>"
                    f"{empty}<td>&nbsp;</td></tr>"
                )
            return (
                f"<h2 style='text-align:center'>Starters List</h2>{info}"
                "<table border='1' cellpadding='6' cellspacing='0'"
                " style='border-collapse:collapse;width:100%'>"
                f"<tr><th>Sail</th><th>Helm</th><th>Boat</th>{lap_cols}<th>Finish</th></tr>"
                f"{rows}</table>"
            )

    def _print_html(self, html: str):
        printer = QPrinter(QPrinter.HighResolution)
        dlg = QPrintDialog(printer, self)
        if dlg.exec() == QPrintDialog.Accepted:
            doc = QTextDocument()
            doc.setHtml(html)
            doc.print_(printer)

    # ── Helpers ─────────────────────────────────────────────────────────

    def _show_warning(self, text: str):
        InfoBar.warning(
            title="Warning",
            content=text,
            parent=self,
            position=InfoBarPosition.TOP_RIGHT,
            duration=3000,
        )

    def closeEvent(self, event):
        self._serial.disconnect_port()
        data.save(self._data)
        event.accept()
