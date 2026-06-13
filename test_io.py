import sys, time
sys.path.insert(0, '.')
import numpy as np
from core.io import (
    export_wav, export_separate_wavs, decode_to_array,
    encode_with_ffmpeg, probe_audio, true_peak_db,
)

RATE = 48000
DUR = 3.0
N = int(RATE * DUR)
LABELS = ['L', 'R', 'C', 'LFE', 'Ls', 'Rs']


def make_tone(freq, amp):
    t = np.arange(N) / RATE
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def test_interleaved_roundtrip(tmp_dir):
    chans = [make_tone(440 + i * 50, 0.3) for i in range(6)]
    data = np.stack(chans, axis=1)  # (N, 6)

    wav_path = f'{tmp_dir}/combo.wav'
    export_wav(data, RATE, wav_path, bit_depth=24)

    info = probe_audio(wav_path)
    print(f"probe interleaved: {info}")
    assert info['channels'] == 6
    assert info['sample_rate'] == RATE

    decoded, rate = decode_to_array(wav_path)
    print(f"decoded shape={decoded.shape} rate={rate}")
    assert decoded.shape[1] == 6
    assert rate == RATE

    # 24-bit PCM -> error de cuantización esperado, tolerancia generosa
    err = np.max(np.abs(decoded - data))
    print(f"error max tras roundtrip 24-bit: {err:.6f}")
    assert err < 1e-3


def test_separate_export(tmp_dir):
    chans = [make_tone(440 + i * 50, 0.3) for i in range(6)]
    paths = export_separate_wavs(chans, LABELS, RATE, f'{tmp_dir}/master', bit_depth=24)
    print(f"archivos separados: {paths}")
    assert len(paths) == 6
    for p, lab in zip(paths, LABELS):
        info = probe_audio(p)
        assert info['channels'] == 1
        assert lab in p


def test_encode_aac_ac3(tmp_dir):
    chans = [make_tone(440 + i * 50, 0.3) for i in range(6)]
    data = np.stack(chans, axis=1)
    wav_path = f'{tmp_dir}/combo.wav'
    export_wav(data, RATE, wav_path)

    aac_path = f'{tmp_dir}/out.aac.mp4'
    encode_with_ffmpeg(wav_path, aac_path, codec='aac', bitrate='448k', extra_args=['-ac', '6'])
    info_aac = probe_audio(aac_path)
    print(f"AAC 5.1: {info_aac}")
    assert info_aac['channels'] == 6

    ac3_path = f'{tmp_dir}/out.ac3.mp4'
    encode_with_ffmpeg(wav_path, ac3_path, codec='eac3', bitrate='448k')
    info_ac3 = probe_audio(ac3_path)
    print(f"E-AC3 5.1: {info_ac3}")
    assert info_ac3['channels'] == 6


def test_true_peak_inter_sample():
    """Una señal cuyo pico real (entre muestras) supera el pico de las muestras."""
    rate = 48000
    # Frecuencia cercana a Nyquist/2 con fase que produce un pico inter-muestra
    t = np.arange(2000) / rate
    sig = (0.999 * np.sin(2 * np.pi * 11025 * t + 0.3)).astype(np.float32)
    sample_peak = 20 * np.log10(np.max(np.abs(sig)))
    tp = true_peak_db(sig)
    print(f"sample peak={sample_peak:.3f} dBFS  true peak={tp:.3f} dBTP")
    assert tp >= sample_peak


def test_true_peak_perf_80min():
    rate = 48000
    n = rate * 80 * 60
    rng = np.random.default_rng(0)
    x = (rng.standard_normal(n) * 0.05).astype(np.float32)
    t0 = time.time()
    tp = true_peak_db(x)
    t1 = time.time()
    print(f"true_peak_db sobre 80min mono: {t1-t0:.2f}s -> {tp:.2f} dBTP")


if __name__ == '__main__':
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmp:
        test_interleaved_roundtrip(tmp)
        test_separate_export(tmp)
        test_encode_aac_ac3(tmp)
    test_true_peak_inter_sample()
    test_true_peak_perf_80min()
    print("OK - todos los tests de io pasan")
