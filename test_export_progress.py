import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import sys, tempfile
sys.path.insert(0, '.')
import numpy as np

from PySide6.QtWidgets import QApplication
from core import io as audio_io
from core.analysis import make_channels, export_master
from ui.main_window import MainWindow, WINDOW_SIZE

RATE = 48000
N = RATE * 2  # 2s


def make_signal(freq=440):
    t = np.arange(N) / RATE
    return (0.2 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def main():
    app = QApplication(sys.argv)

    # --- 1. progreso real de encode_with_ffmpeg ---
    with tempfile.TemporaryDirectory() as tmp:
        wav_path = f"{tmp}/in.wav"
        audio_io.export_wav(make_signal(), RATE, wav_path, bit_depth=24)
        out_path = f"{tmp}/out.m4a"
        pcts = []
        audio_io.encode_with_ffmpeg(wav_path, out_path, codec='aac', bitrate='128k',
                                     progress_cb=pcts.append, duration=2.0)
        assert os.path.exists(out_path)
        assert len(pcts) >= 1, "no se reportó ningún progreso"
        assert pcts[-1] == 100.0, f"el último valor debería ser 100, fue {pcts[-1]}"
        assert all(0 <= p <= 100 for p in pcts)
        print(f"1. Progreso real durante encode AAC: OK ({len(pcts)} muestras, último={pcts[-1]})")

    # --- 2. export_master 5.1 -> AAC con encode_progress_cb ---
    with tempfile.TemporaryDirectory() as tmp:
        channels = make_channels('5.1')
        for i, ch in enumerate(channels):
            p = f"{tmp}/{ch.key}.wav"
            audio_io.export_wav(make_signal(440 + i * 50), RATE, p, bit_depth=24)
            data, rate = audio_io.decode_to_array(p)
            ch.reset()
            ch.data = data[:, 0] if data.ndim > 1 else data
            ch.rate = rate
            ch.duration = ch.data.shape[0] / rate
            ch.file_path = p

        out_dir = f"{tmp}/out"
        enc_pcts = []
        outputs = export_master(channels, '5.1', out_dir, 'master', file_format='aac',
                                 combined=True, encode_progress_cb=enc_pcts.append)
        assert outputs == [f"{out_dir}/master.m4a"]
        assert os.path.exists(outputs[0])
        assert not os.path.exists(f"{out_dir}/master.wav"), "el wav temporal no se limpió"
        assert enc_pcts and enc_pcts[-1] == 100.0
        print(f"2. export_master 5.1->AAC con progreso real: OK ({len(enc_pcts)} muestras)")

    # --- 3. tamaño de ventana se ajusta al contenido sin exceder pantalla ---
    win = MainWindow()
    target_w, target_h = WINDOW_SIZE['5.1']
    screen = win.screen() or QApplication.primaryScreen()
    avail = screen.availableGeometry()
    assert win.width() <= avail.width()
    assert win.height() <= avail.height()
    assert win.width() >= min(target_w, avail.width())
    assert win.height() >= min(target_h, avail.height())
    print(f"3. Ventana ajustada al contenido: {win.width()}x{win.height()} (pantalla {avail.width()}x{avail.height()})")

    # --- 4. combo de idioma no recorta "Español"/"English" ---
    from PySide6.QtGui import QFontMetrics
    fm = QFontMetrics(win.lang_combo.font())
    needed = max(fm.horizontalAdvance("Español"), fm.horizontalAdvance("English")) + 40
    assert win.lang_combo.view().minimumWidth() >= needed
    assert win.lang_combo.minimumContentsLength() >= len("English")
    print("4. Combo de idioma dimensionado correctamente: OK")

    print("\nOK - todas las verificaciones pasan")


if __name__ == '__main__':
    main()
