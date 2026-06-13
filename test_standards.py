import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import sys
sys.path.insert(0, '.')

from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from ui.standards_dialog import StandardsDialog
from ui.i18n import i18n, STANDARDS_TABLE


def main():
    app = QApplication(sys.argv)
    win = MainWindow()

    # --- 1. botón y tooltips presentes en ES ---
    assert win.standards_btn.text() == 'ⓘ Estándares'
    assert 'LUFS' in win.lufs_label.toolTip()
    assert 'Normalizar' in win.target_label.toolTip()
    print("1. Botón y tooltips ES: OK")

    # --- 2. diálogo se abre y muestra la tabla completa ---
    dlg = StandardsDialog(win)
    table = dlg.findChild(__import__('PySide6.QtWidgets', fromlist=['QTableWidget']).QTableWidget)
    rows_es = STANDARDS_TABLE['es']
    assert table.rowCount() == len(rows_es)
    assert table.columnCount() == 4
    assert table.item(0, 0).text() == rows_es[0][0]
    assert table.item(0, 1).text() == '-23 LUFS'
    assert table.horizontalHeaderItem(0).text() == 'Destino'
    print(f"2. Diálogo ES con {table.rowCount()} filas: OK")

    # --- 3. cambio a inglés ---
    win.lang_combo.setCurrentIndex(win.lang_combo.findData('en'))
    assert win.standards_btn.text() == 'ⓘ Standards'
    dlg_en = StandardsDialog(win)
    table_en = dlg_en.findChild(__import__('PySide6.QtWidgets', fromlist=['QTableWidget']).QTableWidget)
    assert table_en.horizontalHeaderItem(0).text() == 'Destination'
    assert table_en.item(0, 0).text() == STANDARDS_TABLE['en'][0][0]
    print("3. Diálogo EN: OK")

    print("\nOK - todas las verificaciones pasan")


if __name__ == '__main__':
    main()
