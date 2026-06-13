"""standards_dialog.py — Ventana de referencia: estándares de loudness y true peak por destino."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QLabel,
)
from PySide6.QtCore import Qt

from ui.i18n import i18n, STANDARDS_TABLE


class StandardsDialog(QDialog):
    """Tabla de referencia de LUFS / True Peak por tipo de entrega."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(i18n.tr('standards_title'))
        self.resize(640, 380)

        layout = QVBoxLayout(self)

        rows = STANDARDS_TABLE.get(i18n.lang, STANDARDS_TABLE['es'])
        table = QTableWidget(len(rows), 4)
        table.setHorizontalHeaderLabels([
            i18n.tr('standards_col_dest'),
            i18n.tr('standards_col_lufs'),
            i18n.tr('standards_col_tp'),
            i18n.tr('standards_col_norm'),
        ])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setWordWrap(True)

        for r, (dest, lufs, tp, norm) in enumerate(rows):
            for c, text in enumerate((dest, lufs, tp, norm)):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                table.setItem(r, c, item)
            table.resizeRowToContents(r)

        layout.addWidget(table)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton(i18n.tr('close'))
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)
