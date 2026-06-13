"""widgets.py — Componentes reutilizables de la interfaz."""

from PySide6.QtWidgets import QWidget, QProgressBar, QDoubleSpinBox
from PySide6.QtCore import Qt, QLocale


class SignedDoubleSpinBox(QDoubleSpinBox):
    """QDoubleSpinBox que muestra siempre el signo (+0.0 / -1.0), con '.' decimal fijo."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLocale(QLocale(QLocale.C))

    def textFromValue(self, value):
        return f"{value:+.1f}"



def db_to_pct(db, lo=-60.0, hi=6.0):
    if db is None:
        return 0
    pct = (db - lo) / (hi - lo) * 100.0
    return max(0, min(100, int(round(pct))))


def meter_color(db, kind='peak'):
    """kind: 'peak' (umbral 0 dBFS) o 'tp' (umbral -1 dBTP)."""
    if db is None:
        return '#5fbe8a'
    limit = -1.0 if kind == 'tp' else 0.0
    if db > limit:
        return '#d4564a'   # rojo
    if db > limit - 8:
        return '#e8a23c'   # ambar
    return '#5fbe8a'       # verde


class MeterBar(QProgressBar):
    """Barra de medidor en dB, sin texto interno, coloreada por umbral."""

    def __init__(self, kind='peak', parent=None):
        super().__init__(parent)
        self.kind = kind
        self.setRange(0, 100)
        self.setValue(0)
        self.setTextVisible(False)
        self.setFixedHeight(6)
        self._apply_color('#5fbe8a')

    def _apply_color(self, color):
        self.setStyleSheet(
            f"QProgressBar {{ background: #26292d; border: none; border-radius: 3px; }}"
            f"QProgressBar::chunk {{ background: {color}; border-radius: 3px; }}"
        )

    def set_db(self, db):
        self.setValue(db_to_pct(db))
        self._apply_color(meter_color(db, self.kind))
