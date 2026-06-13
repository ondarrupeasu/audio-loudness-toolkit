import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import sys, tempfile
sys.path.insert(0, '.')
import numpy as np
from unittest.mock import patch

from PySide6.QtWidgets import QApplication
from core import io as audio_io
from ui.main_window import MainWindow
from ui.player import PlayerWidget
from ui.i18n import i18n

RATE = 48000
N = int(RATE * 1.0)


def make_signal(freq=440):
    t = np.arange(N) / RATE
    return (0.1 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def main():
    app = QApplication(sys.argv)
    win = MainWindow()

    # --- 1. i18n: estado inicial en español ---
    assert i18n.lang == 'es'
    assert win.windowTitle() == 'Verificador de audio — 5.1 / Estéreo / Mono'
    assert win.strips[0].load_btn.text() == 'Cargar archivo'
    assert win.strips[0].sub.text() == 'Front Left'
    assert win.summary_table.horizontalHeaderItem(0).text() == 'Canal'
    assert win.format_combo.itemText(0) == 'WAV (24-bit PCM)'
    assert [win.format_combo.itemData(i) for i in range(win.format_combo.count())] == \
        ['wav', 'flac', 'aac', 'ac3', 'eac3', 'mp3']
    print("1. Estado inicial ES: OK")

    # --- 2. cambiar a inglés conservando selección ---
    win.format_combo.setCurrentIndex(win.format_combo.findData('eac3'))
    win.lang_combo.setCurrentIndex(win.lang_combo.findData('en'))
    assert i18n.lang == 'en'
    assert win.windowTitle() == 'Audio Verifier — 5.1 / Stereo / Mono'
    assert win.strips[0].load_btn.text() == 'Load file'
    assert win.strips[0].sub.text() == 'Front Left'  # mismo en ambos idiomas
    assert win.summary_table.horizontalHeaderItem(0).text() == 'Channel'
    assert win.format_combo.currentData() == 'eac3', "se perdió la selección al traducir"
    assert win.format_combo.currentText() == 'E-AC3 — Dolby Digital Plus (.mp4)'
    print("2. Cambio a EN conservando selección: OK")

    # --- 3. volver a español, comprobar combos de modo ---
    win.lang_combo.setCurrentIndex(win.lang_combo.findData('es'))
    assert win.mode_combo.currentData() == '5.1'
    assert win.mode_combo.currentText() == '5.1 (6 archivos)'
    print("3. Vuelta a ES: OK")

    # --- 4. progreso durante análisis ---
    with tempfile.TemporaryDirectory() as tmp:
        p = f"{tmp}/test_L.wav"
        audio_io.export_wav(make_signal(), RATE, p, bit_depth=24)

        with patch('ui.main_window.QFileDialog.getOpenFileName', return_value=(p, '')):
            win._on_load_clicked(0)
        worker = win.workers[-1]
        # antes de terminar, debería haberse mostrado progreso
        app.processEvents()
        worker.wait()
        for _ in range(10):
            app.processEvents()

        strip = win.strips[0]
        assert strip.progress_bar.isVisible() is False, "la barra debería ocultarse al terminar"
        assert strip.channel.loaded
        assert 'Hz' in strip.status_label.text()
        print("4. Progreso de análisis: OK")

        # --- 5. PlayerWidget recibió el audio ---
        assert strip.player.data is not None
        assert strip.player.rate == RATE
        from ui.player import HAS_SOUNDDEVICE
        assert strip.player.play_btn.isEnabled() is HAS_SOUNDDEVICE
        print(f"5. PlayerWidget cargado (HAS_SOUNDDEVICE={HAS_SOUNDDEVICE}): OK")

        # seek
        strip.player._on_seek(500)  # mitad
        assert abs(strip.player.pos - len(strip.player.data) // 2) < 10
        print("6. Seek del reproductor: OK")

        # --- 7. exportación en segundo plano con progreso ---
        out_dir = f"{tmp}/out"
        os.makedirs(out_dir, exist_ok=True)
        with patch('ui.main_window.QFileDialog.getExistingDirectory', return_value=out_dir):
            win.format_combo.setCurrentIndex(win.format_combo.findData('wav'))
            win._on_export()
        export_worker = win.workers[-1]
        assert win.export_btn.isEnabled() is False
        export_worker.wait()
        for _ in range(10):
            app.processEvents()
        assert win.export_btn.isEnabled() is True
        assert os.path.exists(f"{out_dir}/master.wav")
        assert 'master.wav' in win.export_status.text()
        print("7. Exportación en segundo plano: OK")

    # --- 8. tabla de resumen no editable ---
    from PySide6.QtWidgets import QTableWidget
    assert win.summary_table.editTriggers() == QTableWidget.NoEditTriggers
    print("8. Tabla resumen no editable: OK")

    print("\nOK - todas las nuevas funcionalidades verificadas")


if __name__ == '__main__':
    main()
