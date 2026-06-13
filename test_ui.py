import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import sys, tempfile
sys.path.insert(0, '.')
import numpy as np

from PySide6.QtWidgets import QApplication
from core import io as audio_io
from core.analysis import load_channel_file, analyze_channel
from ui.main_window import MainWindow

RATE = 48000
N = int(RATE * 8.0)


def make_signal(amp, freq, silence_frac=0.3):
    t = np.arange(N) / RATE
    sig = (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    sig[: int(N * silence_frac)] = 0.0
    return sig


def main():
    app = QApplication(sys.argv)
    win = MainWindow()

    assert win.mode == '5.1'
    assert len(win.strips) == 6
    print("Ventana 5.1 creada con 6 tiras OK")

    # cambiar a estéreo y volver a 5.1
    win.mode_combo.setCurrentIndex(1)  # estéreo
    assert win.mode == 'stereo'
    assert len(win.strips) == 2
    print("Cambio a modo estéreo OK (2 tiras)")

    win.mode_combo.setCurrentIndex(0)  # 5.1
    assert win.mode == '5.1'
    assert len(win.strips) == 6
    print("Vuelta a 5.1 OK")

    # simular carga real de los 6 canales (sin worker, directo, para el test)
    with tempfile.TemporaryDirectory() as tmp:
        main_amp = 10 ** (-2.0 / 20.0)
        lfe_amp = 10 ** (-33.0 / 20.0)
        sigs = {
            'L': make_signal(main_amp, 220), 'R': make_signal(main_amp, 221),
            'C': make_signal(main_amp, 110), 'LFE': make_signal(lfe_amp, 50),
            'Ls': make_signal(main_amp * 0.8, 330), 'Rs': make_signal(main_amp * 0.8, 331),
        }
        for idx, ch in enumerate(win.channels):
            p = f"{tmp}/test.{ch.key}.wav"
            audio_io.export_wav(sigs[ch.key], RATE, p, bit_depth=24)
            load_channel_file(ch, p)
            analyze_channel(ch, true_peak_mode='fast')
            win.strips[idx].on_loaded()

        win._update_global()

        print(f"LUFS label: {win.lufs_label.text()}")
        print(f"Delta label: {win.delta_label.text()}")
        print(f"Filtro ffmpeg: {win.ffmpeg_line.text()}")
        assert "LUFS" in win.lufs_label.text()
        assert "pan=5.1" in win.ffmpeg_line.text()

        # tabla resumen
        assert win.summary_table.rowCount() == 6
        row0 = win.summary_table.item(0, 0).text()
        assert row0 == 'L'
        print(f"Resumen fila 0: {[win.summary_table.item(0,c).text() for c in range(4)]}")

        # normalizar
        win._on_normalize()
        print(f"\nTras normalizar:")
        print(f"LUFS label: {win.lufs_label.text()}")
        print(f"Global status: {win.global_status.text()}")
        for idx, ch in enumerate(win.channels):
            print(f"  {ch.label:<5} gain={ch.gain_db:+.2f} dB  spin={win.strips[idx].gain_spin.value():+.1f}")
            assert abs(win.strips[idx].gain_spin.value() - ch.gain_db) < 0.05

        # compensación LFE
        lfe_idx = next(i for i, c in enumerate(win.channels) if c.key == 'LFE')
        before = win.channels[lfe_idx].gain_db
        win._on_lfe_minus10()
        after = win.channels[lfe_idx].gain_db
        print(f"\nLFE -10dB: {before:.1f} -> {after:.1f}")
        assert after == before - 10.0 or after == -24.0

        win._on_lfe_reset()
        assert win.channels[lfe_idx].gain_db == 0.0
        print("Reset LFE OK")

        # exportación combinada a WAV
        win.format_combo.setCurrentIndex(0)  # wav
        win.export_mode_combo.setCurrentIndex(0)  # combinado
        from core.analysis import export_master
        outputs = export_master(win.channels, win.mode, tmp, 'master', file_format='wav', combined=True)
        print(f"\nExportado combinado: {outputs}")
        assert len(outputs) == 1 and outputs[0].endswith('.wav')

        # verificar el wav exportado
        decoded, rate = audio_io.decode_to_array(outputs[0])
        print(f"WAV exportado: shape={decoded.shape} rate={rate}")
        assert decoded.shape[1] == 6
        assert rate == RATE

        # exportación separada a WAV
        outputs_sep = export_master(win.channels, win.mode, tmp, 'master_sep', file_format='wav', combined=False)
        print(f"Exportado separado: {len(outputs_sep)} archivos")
        assert len(outputs_sep) == 6

    print("\nOK - todos los tests de UI pasan")


if __name__ == '__main__':
    main()
