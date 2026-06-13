import sys, tempfile, time
sys.path.insert(0, '.')
import numpy as np

from core import io as audio_io
from core.analysis import (
    make_channels, load_channel_file, analyze_channel,
    integrated_lufs, normalize_main_channels, ffmpeg_pan_filter,
    recompute_true_peak,
)

RATE = 48000
DUR = 8.0  # segundos (suficiente para varios bloques de gateo)
N = int(RATE * DUR)


def make_signal(amp, freq, silence_frac=0.3):
    t = np.arange(N) / RATE
    sig = (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    sig[: int(N * silence_frac)] = 0.0  # tramo de silencio -> fuerza el gateo relativo
    return sig


def build_test_files(tmp_dir):
    """Genera 6 .wav mono que imitan el caso real: picos ~-2dBFS, LFE muy bajo."""
    main_amp = 10 ** (-2.0 / 20.0)   # ~-2 dBFS de pico
    lfe_amp = 10 ** (-33.0 / 20.0)   # ~-33 dBFS de pico

    sigs = {
        'L': make_signal(main_amp, 220),
        'R': make_signal(main_amp, 221),
        'C': make_signal(main_amp, 110),
        'LFE': make_signal(lfe_amp, 50),
        'Ls': make_signal(main_amp * 0.8, 330),
        'Rs': make_signal(main_amp * 0.8, 331),
    }
    paths = {}
    for key, sig in sigs.items():
        p = f"{tmp_dir}/test.{key}.wav"
        audio_io.export_wav(sig, RATE, p, bit_depth=24)
        paths[key] = p
    return paths


def main():
    with tempfile.TemporaryDirectory() as tmp:
        paths = build_test_files(tmp)
        channels = make_channels('5.1')

        t0 = time.time()
        for ch in channels:
            load_channel_file(ch, paths[ch.key])
            analyze_channel(ch, true_peak_mode='fast')
        t1 = time.time()
        print(f"Carga + análisis (true peak rápido) de 6 canales: {t1-t0:.2f}s\n")

        print("Canal  Peak(dBFS)  RMS(dBFS)  TruePeak(dBTP)")
        for ch in channels:
            print(f"{ch.label:<6} {ch.peak_db:>9.1f}  {ch.rms_db:>8.1f}  {ch.true_peak_db:>13.1f}")

        lufs = integrated_lufs(channels)
        print(f"\nLUFS integrado (gateo completo): {lufs:.1f} LUFS")

        # Normalizar a -23 LUFS, debería quedar limitado por el headroom (igual que en la web)
        target = -23.0
        delta, limited, resulting = normalize_main_channels(channels, target)
        print(f"\nNormalizar a {target} LUFS:")
        print(f"  delta aplicado = {delta:+.2f} dB")
        print(f"  limitado por -1 dBTP = {limited}")
        print(f"  LUFS resultante = {resulting:.2f}")
        for ch in channels:
            print(f"  {ch.label:<5} gain={ch.gain_db:+.2f} dB  pico final={ch.display_peak_db():.2f} dBFS  tp final={ch.display_true_peak_db():.2f} dBTP")

        print(f"\nFiltro ffmpeg equivalente:\n  {ffmpeg_pan_filter(channels, '5.1')}")

        # Cambiar el LFE a modo true-peak preciso para ese canal
        lfe = next(c for c in channels if c.key == 'LFE')
        recompute_true_peak(lfe, 'precise')
        print(f"\nLFE true peak (preciso): {lfe.true_peak_db:.2f} dBTP")

        # Tests modo estéreo y mono
        print("\n--- Modo estéreo ---")
        st_channels = make_channels('stereo')
        for ch, key in zip(st_channels, ['L', 'R']):
            load_channel_file(ch, paths[key])
            analyze_channel(ch, true_peak_mode='fast')
        print(f"LUFS estéreo: {integrated_lufs(st_channels):.1f}")
        print(f"Filtro: {ffmpeg_pan_filter(st_channels, 'stereo')}")

        print("\n--- Modo mono ---")
        mo_channels = make_channels('mono')
        load_channel_file(mo_channels[0], paths['C'])
        analyze_channel(mo_channels[0], true_peak_mode='fast')
        print(f"LUFS mono: {integrated_lufs(mo_channels):.1f}")
        mo_channels[0].gain_db = 2.5
        print(f"Filtro (gain +2.5dB): {ffmpeg_pan_filter(mo_channels, 'mono')}")


if __name__ == '__main__':
    main()
