"""Add / Edit racer dialog."""

from PySide6.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QMessageBox
from PySide6.QtGui import QIntValidator

from qfluentwidgets import (
    LineEdit, ComboBox, PrimaryPushButton, PushButton, SubtitleLabel,
)

from boat_handicaps import boat_names, display_name


class RacerDialog(QDialog):
    def __init__(self, parent=None, racer: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Edit Racer" if racer else "Add Racer")
        self.setFixedSize(360, 340)
        self.setModal(True)

        form = QFormLayout(self)
        form.setSpacing(12)
        form.setContentsMargins(20, 20, 20, 20)

        title = SubtitleLabel("Edit Racer" if racer else "Add Racer")
        form.addRow(title)

        self._helm = LineEdit()
        self._helm.setPlaceholderText("Helm name")
        self._crew = LineEdit()
        self._crew.setPlaceholderText("Crew name (optional)")
        self._sail = LineEdit()
        self._sail.setPlaceholderText("Sail number")
        self._sail.setValidator(QIntValidator(0, 999999))
        self._boat = ComboBox()
        self._boat_classes = boat_names()
        self._boat.addItems([display_name(n) for n in self._boat_classes])

        if racer:
            self._helm.setText(racer.get("helm", ""))
            self._crew.setText(racer.get("crew", ""))
            self._sail.setText(str(racer.get("sailNo", "")))
            try:
                idx = self._boat_classes.index(racer.get("boatClass", ""))
                self._boat.setCurrentIndex(idx)
            except ValueError:
                pass

        form.addRow("Helm:", self._helm)
        form.addRow("Crew:", self._crew)
        form.addRow("Sail No:", self._sail)
        form.addRow("Boat:", self._boat)

        btn_row = QHBoxLayout()
        save_btn = PrimaryPushButton("Save")
        save_btn.clicked.connect(self._validate)
        cancel_btn = PushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        form.addRow(btn_row)

    def _validate(self):
        helm = self._helm.text().strip()
        crew = self._crew.text().strip()
        sail = self._sail.text().strip()

        ok = lambda s: all(c.isalpha() or c.isspace() for c in s)

        if not helm:
            QMessageBox.warning(self, "Error", "Helm cannot be empty.")
            return
        if not ok(helm) or (crew and not ok(crew)):
            QMessageBox.warning(self, "Error",
                                "Helm and Crew must only contain letters.")
            return
        if not sail.isdigit():
            QMessageBox.warning(self, "Error",
                                "Sail number must only contain digits.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "helm":      self._helm.text().strip(),
            "crew":      self._crew.text().strip(),
            "sailNo":    self._sail.text().strip(),
            "boatClass": self._boat_classes[self._boat.currentIndex()],
        }
