import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import sys, tempfile
sys.path.insert(0, '.')
import numpy as np
from unittest.mock import patch

from PySide6.QtWidgets import QApplication
from core import io as audio_io
from core.analysis import export_master
from ui.main_window import MainWindow

RATE = 48000
N = RATE


def make_signal():
    t = np.arange(N) / RATE
    return (0.1 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)


def main():
    app = QApplication(sys.argv)
    win = MainWindow()

    with tempfile.TemporaryDirectory() as tmp:
        p = f"{tmp}/test_L.wav"
        audio_io.export_wav(make_signal(), RATE, p, bit_depth=24)
        with patch('ui.main_window.QFileDialog.getOpenFileName', return_value=(p, '')):
            win._on_load_clicked(0)
        worker = win.workers[-1]
        worker.wait()
        for _ in range(10):
            app.processEvents()

        strip = win.strips[0]

        # --- 1. spinbox y botones -/+ ---
        assert strip.gain_spin.isEnabled()
        assert strip.gain_down_btn.isEnabled()
        assert strip.gain_up_btn.isEnabled()

        strip.gain_spin.setValue(-10.0)
        assert strip.gain_spin.text() == "-10.0 dB"
        assert abs(strip.channel.gain_db - (-10.0)) < 1e-6

        strip.gain_spin.setValue(2.5)
        assert abs(strip.channel.gain_db - 2.5) < 1e-6
        print("1. Spinbox de ganancia: OK")

        # spin arrows = pasos de 0.1 dB
        strip.gain_spin.setValue(0.0)
        strip.gain_up_btn.click()
        assert abs(strip.gain_spin.value() - 0.1) < 1e-6
        for _ in range(10):
            strip.gain_down_btn.click()
        assert abs(strip.gain_spin.value() - (-0.9)) < 1e-6
        print("2. Botones -/+ (paso 0.1 dB): OK")

        # signo siempre visible
        strip.gain_spin.setValue(0.0)
        assert strip.gain_spin.text() == "+0.0 dB"
        print("3. Signo +/- siempre visible: OK")

        # --- 4. export_master limpia el .wav temporal si ffmpeg falla ---
        out_dir = f"{tmp}/out"
        os.makedirs(out_dir, exist_ok=True)
        with patch.object(audio_io, 'FFMPEG', '/ruta/que/no/existe/ffmpeg'):
            try:
                export_master(win.channels, win.mode, out_dir, "master", file_format='aac')
                assert False, "debería haber lanzado un error"
            except RuntimeError as exc:
                assert "imageio-ffmpeg" in str(exc) or "ffmpeg" in str(exc)
        # no debe quedar ningún wav/archivo a medias
        leftover = os.listdir(out_dir)
        assert leftover == [], f"quedaron archivos sin limpiar: {leftover}"
        print("4. Limpieza tras fallo de ffmpeg (sin .wav residual): OK")

    print("\nOK - todas las verificaciones pasan")


if __name__ == '__main__':
    main()
