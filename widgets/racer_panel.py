"""Left panel — racer list with search, CRUD, and participation checkboxes."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt, Signal

from qfluentwidgets import (
    SearchLineEdit, PushButton, PrimaryPushButton, CheckBox,
    CardWidget, BodyLabel, CaptionLabel, SubtitleLabel,
    SmoothScrollArea, FluentIcon as FIF, MessageBox,
)

import data
from .racer_dialog import RacerDialog


class RacerPanel(QWidget):
    participation_changed = Signal(list)

    def __init__(self, store: dict, parent=None):
        super().__init__(parent)
        self._store = store
        self._racers: list[dict] = store["racers"]
        self._participating: list[dict] = []
        self._participating_ids: set = set()
        self._editable = True

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        title = SubtitleLabel("Racers")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self._search = SearchLineEdit()
        self._search.setPlaceholderText("Search by helm name…")
        self._search.textChanged.connect(self._filter)
        layout.addWidget(self._search)

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

        self._add_btn = PrimaryPushButton(FIF.ADD, "Add Racer")
        self._add_btn.clicked.connect(self._add_racer)
        layout.addWidget(self._add_btn)

        self.refresh()

    # ── Public ──────────────────────────────────────────────────────────

    @property
    def participating(self) -> list[dict]:
        return list(self._participating)

    def refresh(self):
        while self._card_layout.count():
            item = self._card_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for i, racer in enumerate(self._racers):
            self._card_layout.addWidget(self._make_card(racer, i))
        self._filter(self._search.text())

    def set_editable(self, enabled: bool):
        self._editable = enabled
        self._add_btn.setEnabled(enabled)
        self._search.setEnabled(enabled)

    # ── Card builder ────────────────────────────────────────────────────

    def _make_card(self, racer: dict, index: int) -> CardWidget:
        card = CardWidget()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(2)

        top = QHBoxLayout()
        cb = CheckBox()
        cb.setChecked(racer["id"] in self._participating_ids)
        cb.toggled.connect(lambda checked, r=racer: self._toggle(r, checked))
        top.addWidget(cb)
        top.addWidget(BodyLabel(f"Helm: {racer['helm']}"))
        top.addStretch()
        lay.addLayout(top)

        if racer.get("crew") and racer["crew"] != "none":
            lay.addWidget(CaptionLabel(f"  Crew: {racer['crew']}"))
        lay.addWidget(CaptionLabel(f"  Boat: {racer['boatClass']}  |  Sail: {racer['sailNo']}"))

        btn_row = QHBoxLayout()
        edit_btn = PushButton("Edit")
        edit_btn.setFixedHeight(28)
        edit_btn.clicked.connect(lambda _, idx=index: self._edit_racer(idx))
        del_btn = PushButton("Delete")
        del_btn.setFixedHeight(28)
        del_btn.clicked.connect(lambda _, idx=index: self._delete_racer(idx))
        btn_row.addWidget(edit_btn)
        btn_row.addWidget(del_btn)
        lay.addLayout(btn_row)

        card._helm_name = racer["helm"].upper()
        return card

    # ── Actions ─────────────────────────────────────────────────────────

    def _toggle(self, racer: dict, checked: bool):
        rid = racer["id"]
        if checked:
            if rid not in self._participating_ids:
                self._participating_ids.add(rid)
                self._participating.append(racer)
        else:
            self._participating_ids.discard(rid)
            self._participating = [
                r for r in self._participating if r["id"] != rid
            ]
        self.participation_changed.emit(self._participating)

    def _add_racer(self):
        if not self._editable:
            return
        dlg = RacerDialog(self.window())
        if dlg.exec() == RacerDialog.Accepted:
            info = dlg.get_data()
            info["id"] = self._store["next_id"]
            self._store["next_id"] += 1
            self._racers.append(info)
            data.save(self._store)
            self.refresh()

    def _edit_racer(self, index: int):
        if not self._editable:
            return
        racer = self._racers[index]
        dlg = RacerDialog(self.window(), racer)
        if dlg.exec() == RacerDialog.Accepted:
            racer.update(dlg.get_data())
            data.save(self._store)
            self.refresh()

    def _delete_racer(self, index: int):
        if not self._editable:
            return
        msg = MessageBox("Confirm", "Delete this racer?", self.window())
        if msg.exec():
            removed = self._racers.pop(index)
            self._participating_ids.discard(removed["id"])
            self._participating = [
                r for r in self._participating if r["id"] != removed["id"]
            ]
            data.save(self._store)
            self.refresh()
            self.participation_changed.emit(self._participating)

    def _filter(self, text: str):
        text = text.upper()
        for i in range(self._card_layout.count()):
            w = self._card_layout.itemAt(i).widget()
            if w:
                w.setVisible(text in getattr(w, "_helm_name", ""))
