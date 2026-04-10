"""Left panel — racer list with search, CRUD, and participation checkboxes."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFontMetrics

from qfluentwidgets import (
    SearchLineEdit, PushButton, PrimaryPushButton, CheckBox,
    CardWidget, BodyLabel, CaptionLabel, SubtitleLabel,
    SmoothScrollArea, FluentIcon as FIF, MessageBox,
    TransparentToolButton,
)

import data
from boat_handicaps import display_name
from .racer_dialog import RacerDialog


class _ElidedLabel(QLabel):
    """A QLabel that elides text with '…' when it doesn't fit."""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._full_text = text
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setMinimumWidth(0)

    def setText(self, text: str):
        self._full_text = text
        super().setText(text)
        self._elide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._elide()

    def _elide(self):
        fm = QFontMetrics(self.font())
        elided = fm.elidedText(self._full_text, Qt.ElideRight, self.width())
        super().setText(elided)
        self.setToolTip(self._full_text if elided != self._full_text else "")


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
        self._search.setPlaceholderText("Search by name or sail number…")
        self._search.textChanged.connect(self._filter)
        layout.addWidget(self._search)

        self._select_all = CheckBox("Select All")
        self._select_all.toggled.connect(self._toggle_all)
        layout.addWidget(self._select_all)

        self._scroll = SmoothScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self._container = QWidget()
        self._container.setStyleSheet("QWidget { background: transparent; }")
        self._card_layout = QVBoxLayout(self._container)
        self._card_layout.setAlignment(Qt.AlignTop)
        self._card_layout.setSpacing(4)
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
        # Add button and search stay enabled to allow adding entries during race

    # ── Card builder ────────────────────────────────────────────────────

    def _make_card(self, racer: dict, index: int) -> CardWidget:
        card = CardWidget()
        card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        lay = QHBoxLayout(card)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(6)

        cb = CheckBox()
        cb.setChecked(racer["id"] in self._participating_ids)
        cb.toggled.connect(lambda checked, r=racer: self._toggle(r, checked))
        lay.addWidget(cb, 0, Qt.AlignVCenter)

        info = QVBoxLayout()
        info.setSpacing(0)
        info.setContentsMargins(0, 0, 0, 0)

        name_label = _ElidedLabel(f"#{racer['sailNo']}  {racer['helm']}")
        name_label.setStyleSheet(BodyLabel().styleSheet())
        info.addWidget(name_label)

        detail = display_name(racer['boatClass'])
        crew = racer.get("crew", "")
        if crew and crew.lower() != "none":
            detail += f"  ·  Crew: {crew}"
        detail_label = _ElidedLabel(detail)
        detail_label.setStyleSheet(CaptionLabel().styleSheet())
        info.addWidget(detail_label)
        lay.addLayout(info, 1)

        edit_btn = TransparentToolButton(FIF.EDIT)
        edit_btn.setFixedSize(30, 30)
        edit_btn.setEnabled(self._editable)
        edit_btn.clicked.connect(lambda _, idx=index: self._edit_racer(idx))
        lay.addWidget(edit_btn, 0, Qt.AlignVCenter)

        del_btn = TransparentToolButton(FIF.DELETE)
        del_btn.setFixedSize(30, 30)
        del_btn.setEnabled(self._editable)
        del_btn.clicked.connect(lambda _, idx=index: self._delete_racer(idx))
        lay.addWidget(del_btn, 0, Qt.AlignVCenter)

        card._search_text = f"{racer['helm'].upper()} {racer['sailNo']}"
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

    def _toggle_all(self, checked: bool):
        if checked:
            for racer in self._racers:
                if racer["id"] not in self._participating_ids:
                    self._participating_ids.add(racer["id"])
                    self._participating.append(racer)
        else:
            self._participating_ids.clear()
            self._participating.clear()
        self.participation_changed.emit(self._participating)
        self.refresh()

    def _add_racer(self):
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
                w.setVisible(text in getattr(w, "_search_text", ""))
