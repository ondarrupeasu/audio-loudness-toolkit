import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import sys, tempfile
sys.path.insert(0, '.')
import numpy as np
from unittest.mock import patch

from PySide6.QtWidgets import QApplication
from core import io as audio_io
from ui.main_window import MainWindow

RATE = 48000
N = int(RATE * 2.0)


def make_signal(freq):
    t = np.arange(N) / RATE
    return (0.1 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def main():
    app = QApplication(sys.argv)
    win = MainWindow()

    with tempfile.TemporaryDirectory() as tmp:
        labels = ['L', 'R', 'C', 'LFE', 'Ls', 'Rs']
        paths = {}
        for i, lab in enumerate(labels):
            p = f"{tmp}/test_{lab}.wav"
            audio_io.export_wav(make_signal(440 + i * 100), RATE, p, bit_depth=24)
            paths[lab] = p

        for idx, lab in enumerate(labels):
            with patch('ui.main_window.QFileDialog.getOpenFileName', return_value=(paths[lab], '')):
                win._on_load_clicked(idx)
            worker = win.workers[-1]
            worker.wait()
            for _ in range(10):
                app.processEvents()

        print("idx  key   channel.file_path                         strip.fname_label")
        for idx, ch in enumerate(win.channels):
            fname = win.strips[idx].fname_label.text()
            print(f"{idx:>3}  {ch.key:<5} {os.path.basename(str(ch.file_path)):<40} {fname}")
            expected = f"test_{labels[idx]}.wav"
            assert os.path.basename(str(ch.file_path)) == expected, \
                f"Canal {idx} ({ch.key}) tiene {ch.file_path}, esperaba {expected}"
            assert fname == expected, f"Strip {idx} muestra '{fname}', esperaba '{expected}'"

    print("\nOK - cada canal recibió su archivo correcto")


if __name__ == '__main__':
    main()
