#!/usr/bin/env python3
"""ESC Race Box — Sailing Race Timer (entry point)."""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QFontDatabase, QColor

from qfluentwidgets import setTheme, Theme, setThemeColor

from window import MainWindow


def main():
    app = QApplication(sys.argv)

    setTheme(Theme.DARK)
    setThemeColor(QColor("#FFC0DB"))

    font_path = Path(__file__).parent / "Jua-Regular.ttf"
    if font_path.exists():
        QFontDatabase.addApplicationFont(str(font_path))
        app.setFont(QFont("Jua", 11))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
