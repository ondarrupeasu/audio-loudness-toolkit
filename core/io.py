"""
io.py — Entrada/salida de audio multi-formato vía ffmpeg + soundfile.

- decode_to_array: cualquier formato que ffmpeg entienda (.wav, .aiff, .mp3, .aac, .flac...)
  -> numpy array (samples, channels) float32, preservando el sample rate original.
- export_wav / export_separate_wavs: WAV (16/24/32-bit) interleaved o un archivo por canal.
- encode_with_ffmpeg: WAV -> cualquier codec soportado (aac, ac3, eac3, flac, mp3...).
- true_peak_db: estimación de true peak por sobremuestreo (scipy.signal.resample_poly).
"""

import os
import re
import subprocess
from fractions import Fraction

import numpy as np
import soundfile as sf
import imageio_ffmpeg
from scipy.signal import resample_poly

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def check_ffmpeg():
    """Comprueba que el binario embebido de ffmpeg existe y es ejecutable.

    Si la instalación de 'imageio-ffmpeg' quedó incompleta (binario no
    descargado/extraído), lanza un error con instrucciones claras en vez
    del FileNotFoundError críptico de subprocess.
    """
    if not os.path.isfile(FFMPEG):
        raise RuntimeError(
            "No se encuentra el ejecutable de ffmpeg embebido en:\n"
            f"  {FFMPEG}\n\n"
            "La instalación de 'imageio-ffmpeg' está incompleta (falta el binario). "
            "Soluciónalo así:\n"
            "  pip uninstall imageio-ffmpeg -y\n"
            "  pip install --no-cache-dir imageio-ffmpeg\n"
            "Y comprueba con:\n"
            '  python3 -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"'
        )
    if not os.access(FFMPEG, os.X_OK):
        try:
            os.chmod(FFMPEG, 0o755)
        except OSError:
            raise RuntimeError(f"El ejecutable de ffmpeg no tiene permisos de ejecución: {FFMPEG}")


_LAYOUT_CHANNELS = {
    'mono': 1,
    'stereo': 2,
    '5.1': 6,
    '5.1(side)': 6,
}


def probe_audio(path):
    """Devuelve {'sample_rate', 'channels', 'duration'} leyendo la salida de ffmpeg -i."""
    proc = subprocess.run([FFMPEG, '-i', str(path)], capture_output=True, text=True)
    stderr = proc.stderr

    m = re.search(r'Audio:.*?, (\d+) Hz, ([\w\.\(\)]+)', stderr)
    if not m:
        raise ValueError(f"No se pudo leer el stream de audio de '{path}':\n{stderr}")
    rate = int(m.group(1))
    layout = m.group(2)

    channels = _LAYOUT_CHANNELS.get(layout)
    if channels is None:
        cm = re.match(r'(\d+) channels?', layout)
        channels = int(cm.group(1)) if cm else 1

    duration = None
    dm = re.search(r'Duration: (\d+):(\d+):([\d.]+)', stderr)
    if dm:
        h, mi, s = dm.groups()
        duration = int(h) * 3600 + int(mi) * 60 + float(s)

    return {'sample_rate': rate, 'channels': channels, 'duration': duration}


def decode_to_array(path):
    """
    Decodifica cualquier formato soportado por ffmpeg a un array float32
    de forma (samples, channels), conservando el sample rate original.
    """
    info = probe_audio(path)
    cmd = [FFMPEG, '-v', 'error', '-i', str(path), '-f', 'f32le', '-acodec', 'pcm_f32le', '-']
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode(errors='ignore'))

    data = np.frombuffer(proc.stdout, dtype=np.float32)
    channels = info['channels']
    if channels > 1:
        data = data.reshape(-1, channels)
    return data, info['sample_rate']


_SUBTYPES = {16: 'PCM_16', 24: 'PCM_24', 32: 'PCM_32'}


def export_wav(data, rate, path, bit_depth=24):
    """data: (samples, channels) o (samples,) float. Exporta un único WAV interleaved."""
    sf.write(str(path), data, rate, subtype=_SUBTYPES[bit_depth])


def export_separate_wavs(channels, labels, rate, base_path, bit_depth=24):
    """
    channels: lista de arrays mono (samples,).
    labels:   lista de etiquetas (mismo orden) para nombrar los archivos.
    base_path: ruta sin extensión, ej. '/.../master' -> master.L.wav, master.R.wav...
    Devuelve la lista de rutas creadas.
    """
    paths = []
    for arr, label in zip(channels, labels):
        p = f"{base_path}.{label}.wav"
        sf.write(p, arr, rate, subtype=_SUBTYPES[bit_depth])
        paths.append(p)
    return paths


_OUT_TIME_RE = re.compile(r'out_time_ms=(-?\d+)')


def encode_with_ffmpeg(wav_path, out_path, codec, bitrate=None, extra_args=None,
                        progress_cb=None, duration=None):
    """Codifica un WAV a cualquier formato/codec soportado por ffmpeg.

    Si se pasa progress_cb(pct) y duration (segundos), se reporta el
    progreso real de la codificación leyendo -progress pipe:1.
    """
    check_ffmpeg()
    cmd = [FFMPEG, '-y', '-v', 'error']
    if progress_cb and duration:
        cmd += ['-progress', 'pipe:1', '-nostats']
    cmd += ['-i', str(wav_path), '-c:a', codec]
    if bitrate:
        cmd += ['-b:a', bitrate]
    if extra_args:
        cmd += extra_args
    cmd.append(str(out_path))

    if not (progress_cb and duration):
        try:
            proc = subprocess.run(cmd, capture_output=True)
        except FileNotFoundError as exc:
            raise RuntimeError(f"No se pudo ejecutar ffmpeg ({FFMPEG}): {exc}")
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.decode(errors='ignore'))
        return

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError(f"No se pudo ejecutar ffmpeg ({FFMPEG}): {exc}")

    for line in proc.stdout:
        m = _OUT_TIME_RE.search(line)
        if m:
            out_us = int(m.group(1))
            if out_us >= 0:
                pct = min(100.0, out_us / 1_000_000 / duration * 100.0)
                progress_cb(pct)

    stderr = proc.stderr.read()
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(stderr)
    progress_cb(100.0)


def resample_to(data, orig_rate, target_rate):
    """Resampleo racional (polifásico) de una señal mono a target_rate."""
    if orig_rate == target_rate:
        return data
    frac = Fraction(target_rate, orig_rate).limit_denominator(1000)
    up, down = frac.numerator, frac.denominator
    return resample_poly(data, up, down).astype(np.float32)


def true_peak_db(mono, oversample=4, chunk_size=500_000, overlap=2000):
    """
    True peak aproximado por sobremuestreo polifásico, procesado por bloques
    para no materializar el array sobremuestreado completo en memoria
    (resample_poly produce float64 a oversample x el tamaño de entrada).
    """
    if mono.size == 0:
        return float('-inf')
    if oversample <= 1:
        return 20 * np.log10(max(np.max(np.abs(mono)), 1e-10))

    n = mono.shape[0]
    if n <= chunk_size:
        sig = resample_poly(mono, oversample, 1)
        return 20 * np.log10(max(np.max(np.abs(sig)), 1e-10))

    step = chunk_size - overlap
    peak = 0.0
    start = 0
    while start < n:
        end = min(start + chunk_size, n)
        chunk = mono[start:end]
        sig = resample_poly(chunk, oversample, 1)
        c_peak = np.max(np.abs(sig))
        if c_peak > peak:
            peak = c_peak
        if end == n:
            break
        start += step

    return 20 * np.log10(max(peak, 1e-10))
