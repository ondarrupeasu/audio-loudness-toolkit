import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

DARK_QSS = """
QWidget { background: #16181a; color: #e7e5df; font-size: 12px; }
QGroupBox { border: 1px solid #383c40; border-radius: 8px; margin-top: 8px; padding-top: 12px; font-weight: bold; }
QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
QPushButton { background: #26292d; border: 1px solid #383c40; border-radius: 4px; padding: 4px 8px; }
QPushButton:hover { border-color: #8a5530; }
QPushButton:disabled { color: #5a5854; }
QLineEdit, QComboBox, QDoubleSpinBox, QTableWidget { background: #26292d; border: 1px solid #383c40; border-radius: 4px; padding: 2px 4px; }
QDoubleSpinBox { padding-right: 2px; }
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    width: 18px;
    border-left: 1px solid #383c40;
    background: #2f3338;
}
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover { background: #383c40; }
QDoubleSpinBox::up-arrow, QDoubleSpinBox::down-arrow { width: 9px; height: 9px; }
QSlider::groove:vertical { background: #26292d; width: 6px; border-radius: 3px; }
QSlider::handle:vertical { background: #d9854a; height: 14px; margin: 0 -4px; border-radius: 4px; }
QHeaderView::section { background: #1f2225; border: none; padding: 4px; }
"""


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_QSS)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
