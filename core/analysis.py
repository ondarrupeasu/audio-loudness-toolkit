"""
analysis.py — Orquestación: une io.py y loudness.py en torno a un objeto Channel
por pista, y expone las operaciones de alto nivel que usará la UI.
"""

from dataclasses import dataclass, field
from typing import Optional, List
import numpy as np

from . import io as audio_io
from . import loudness


# Configuración de canales por modo (orden SMPTE/ffmpeg para 5.1)
MODE_CONFIGS = {
    '5.1': [
        {'key': 'L',   'label': 'L',   'name': 'ch_front_left',     'weight': 1.0,  'pan': 'FL'},
        {'key': 'R',   'label': 'R',   'name': 'ch_front_right',    'weight': 1.0,  'pan': 'FR'},
        {'key': 'C',   'label': 'C',   'name': 'ch_center',         'weight': 1.0,  'pan': 'FC'},
        {'key': 'LFE', 'label': 'LFE', 'name': 'ch_lfe',            'weight': 0.0,  'pan': 'LFE'},
        {'key': 'Ls',  'label': 'Ls',  'name': 'ch_surround_left',  'weight': 1.41, 'pan': 'BL'},
        {'key': 'Rs',  'label': 'Rs',  'name': 'ch_surround_right', 'weight': 1.41, 'pan': 'BR'},
    ],
    'stereo': [
        {'key': 'L', 'label': 'L', 'name': 'ch_left', 'weight': 1.0, 'pan': 'FL'},
        {'key': 'R', 'label': 'R', 'name': 'ch_right', 'weight': 1.0, 'pan': 'FR'},
    ],
    'mono': [
        {'key': 'M', 'label': 'M', 'name': 'ch_mono', 'weight': 1.0, 'pan': 'c0'},
    ],
}

TRUE_PEAK_MODES = {
    'precise': 4,   # sobremuestreo x4, ~16s/canal en 80min
    'fast': 1,      # pico de muestra, instantáneo
}


@dataclass
class Channel:
    key: str
    label: str
    name: str
    weight: float
    pan: str

    file_path: Optional[str] = None
    data: Optional[np.ndarray] = None       # señal mono original (samples,)
    rate: Optional[int] = None
    duration: Optional[float] = None

    gain_db: float = 0.0

    peak_db: Optional[float] = None
    rms_db: Optional[float] = None
    true_peak_db: Optional[float] = None
    true_peak_mode: Optional[str] = None
    z: Optional[np.ndarray] = None          # bloques K-weighted para loudness

    @property
    def loaded(self):
        return self.data is not None

    def reset(self):
        self.file_path = None
        self.data = None
        self.rate = None
        self.duration = None
        self.gain_db = 0.0
        self.peak_db = None
        self.rms_db = None
        self.true_peak_db = None
        self.true_peak_mode = None
        self.z = None

    # --- valores derivados de la ganancia actual ---
    def display_peak_db(self):
        return self.peak_db + self.gain_db if self.peak_db is not None else None

    def display_rms_db(self):
        return self.rms_db + self.gain_db if self.rms_db is not None else None

    def display_true_peak_db(self):
        return self.true_peak_db + self.gain_db if self.true_peak_db is not None else None

    def mean_square_kw(self, gain_db=None):
        """z escalado a la ganancia dada (o la actual)."""
        if self.z is None:
            return None
        g = self.gain_db if gain_db is None else gain_db
        return self.z * (10 ** (g / 10.0))


def make_channels(mode):
    """Crea la lista de Channel para el modo dado ('5.1' / 'stereo' / 'mono')."""
    return [Channel(**cfg) for cfg in MODE_CONFIGS[mode]]


def load_channel_file(channel, path):
    """Decodifica un archivo (cualquier formato soportado por ffmpeg) en el canal.
    Si el archivo tiene más de 1 canal, se usa el primero (canal 0)."""
    data, rate = audio_io.decode_to_array(path)
    if data.ndim > 1:
        mono = data[:, 0].copy()
        extra_channels = data.shape[1]
    else:
        mono = data
        extra_channels = 1

    channel.reset()
    channel.file_path = path
    channel.data = mono
    channel.rate = rate
    channel.duration = mono.shape[0] / rate
    return extra_channels


def load_stereo_split(path):
    """Decodifica un archivo estéreo y devuelve (mono_L, mono_R, rate).
    Lanza ValueError si el archivo no tiene al menos 2 canales."""
    data, rate = audio_io.decode_to_array(path)
    if data.ndim < 2 or data.shape[1] < 2:
        raise ValueError("El archivo no tiene al menos 2 canales")
    return data[:, 0].copy(), data[:, 1].copy(), rate


def analyze_channel(channel, true_peak_mode='precise', progress_cb=None):
    """Calcula peak/RMS/true peak y el z cacheado para loudness (gain=0)."""
    data = channel.data
    rate = channel.rate

    peak = np.max(np.abs(data)) if data.size else 0.0
    rms = np.sqrt(np.mean(data.astype(np.float64) ** 2)) if data.size else 0.0
    channel.peak_db = 20 * np.log10(max(peak, 1e-10))
    channel.rms_db = 20 * np.log10(max(rms, 1e-10))

    if progress_cb:
        progress_cb('true_peak')
    oversample = TRUE_PEAK_MODES[true_peak_mode]
    channel.true_peak_db = audio_io.true_peak_db(data, oversample=oversample)
    channel.true_peak_mode = true_peak_mode

    if progress_cb:
        progress_cb('loudness')
    kw = loudness.k_weight(data.astype(np.float64), rate)
    channel.z = loudness.block_meansquares(kw, rate)

    if progress_cb:
        progress_cb('done')


def recompute_true_peak(channel, true_peak_mode):
    """Recalcula solo el true peak (p.ej. al cambiar de modo rápido a preciso)."""
    oversample = TRUE_PEAK_MODES[true_peak_mode]
    channel.true_peak_db = audio_io.true_peak_db(channel.data, oversample=oversample)
    channel.true_peak_mode = true_peak_mode


def integrated_lufs(channels):
    """LUFS integrado (gateo completo) a partir de los z cacheados y ganancias actuales."""
    loaded = [c for c in channels if c.z is not None]
    if not loaded:
        return None
    z_list = [c.mean_square_kw() for c in loaded]
    gains = [0.0] * len(loaded)  # ya incorporado en mean_square_kw
    G = [c.weight for c in loaded]
    if all(g == 0.0 for g in G):
        return None
    return loudness.gated_loudness(z_list, gains, G)


def normalize_main_channels(channels, target_lufs, headroom_dbtp=-1.0):
    """
    Ajusta la ganancia de los canales con weight > 0 para alcanzar target_lufs,
    limitando el ajuste para no superar headroom_dbtp en ningún canal principal.

    Devuelve (delta_aplicado_db, limitado: bool, lufs_resultante).
    """
    current = integrated_lufs(channels)
    if current is None:
        return None, False, None

    delta = target_lufs - current

    main = [c for c in channels if c.weight > 0 and c.true_peak_db is not None]
    if main:
        max_tp = max(c.display_true_peak_db() for c in main)
        headroom_available = headroom_dbtp - max_tp
        limited = delta > headroom_available
        if limited:
            delta = headroom_available
    else:
        limited = False

    for c in channels:
        if c.weight > 0 and c.z is not None:
            c.gain_db = max(-60.0, min(12.0, c.gain_db + delta))

    resulting = integrated_lufs(channels)
    return delta, limited, resulting


def export_master(channels, mode, out_dir, base_name, file_format='wav',
                   combined=True, bit_depth=24, progress_cb=None, encode_progress_cb=None):
    """
    Exporta el máster con las ganancias actuales aplicadas.

    mode        : '5.1' | 'stereo' | 'mono' (determina nº de canales / channel mask)
    out_dir     : directorio destino
    base_name   : nombre base sin extensión (ej. 'master')
    file_format : 'wav' | 'flac' | 'aac' | 'eac3'
    combined    : True -> un archivo interleaved; False -> un archivo por canal
    Devuelve la lista de rutas generadas.
    """
    import os

    loaded = [c for c in channels if c.loaded]
    if not loaded:
        raise ValueError("No hay ningún canal cargado")

    target_rate = max(c.rate for c in loaded)

    arrays = []
    for c in channels:
        if progress_cb:
            progress_cb(c.label)
        if c.loaded:
            arr = audio_io.resample_to(c.data, c.rate, target_rate)
            arr = arr.astype(np.float64) * (10 ** (c.gain_db / 20.0))
            arr = np.clip(arr, -1.0, 1.0).astype(np.float32)
        else:
            arr = None
        arrays.append(arr)

    max_len = max(a.shape[0] for a in arrays if a is not None)
    for i, a in enumerate(arrays):
        if a is None:
            arrays[i] = np.zeros(max_len, dtype=np.float32)
        elif a.shape[0] < max_len:
            arrays[i] = np.pad(a, (0, max_len - a.shape[0]))

    labels = [c.label for c in channels]
    os.makedirs(out_dir, exist_ok=True)
    outputs = []

    if combined:
        interleaved = np.stack(arrays, axis=1)
        wav_path = os.path.join(out_dir, f"{base_name}.wav")
        audio_io.export_wav(interleaved, target_rate, wav_path, bit_depth=bit_depth)

        if file_format == 'wav':
            outputs.append(wav_path)
        else:
            ext_map = {'flac': ('flac', 'flac', None, None),
                       'aac': ('m4a', 'aac', '448k', ['-ac', str(len(channels))]),
                       'eac3': ('mp4', 'eac3', '448k', None),
                       'ac3': ('ac3.mp4', 'ac3', '448k', None),
                       'mp3': ('mp3', 'libmp3lame', '192k', ['-ac', '2'] if len(channels) > 2 else None)}
            if file_format not in ext_map:
                os.remove(wav_path)
                raise ValueError(f"Formato no soportado: {file_format}")
            ext, codec, bitrate, extra = ext_map[file_format]
            out_path = os.path.join(out_dir, f"{base_name}.{ext}")
            duration = max_len / target_rate
            try:
                audio_io.encode_with_ffmpeg(wav_path, out_path, codec=codec, bitrate=bitrate, extra_args=extra,
                                             progress_cb=encode_progress_cb, duration=duration)
            except Exception:
                if os.path.exists(out_path):
                    os.remove(out_path)
                raise
            finally:
                if os.path.exists(wav_path):
                    os.remove(wav_path)
            outputs.append(out_path)

    else:
        n_files = len(arrays)
        for file_idx, (arr, label) in enumerate(zip(arrays, labels)):
            wav_path = os.path.join(out_dir, f"{base_name}.{label}.wav")
            audio_io.export_wav(arr, target_rate, wav_path, bit_depth=bit_depth)

            if file_format == 'wav':
                outputs.append(wav_path)
            else:
                ext = {'flac': 'flac', 'aac': 'm4a', 'eac3': 'mp4', 'ac3': 'mp4', 'mp3': 'mp3'}[file_format]
                codec = {'flac': 'flac', 'aac': 'aac', 'eac3': 'eac3', 'ac3': 'ac3', 'mp3': 'libmp3lame'}[file_format]
                bitrate = None if file_format == 'flac' else '192k'
                out_path = os.path.join(out_dir, f"{base_name}.{label}.{ext}")
                duration = arr.shape[0] / target_rate

                def _file_progress(pct, _idx=file_idx):
                    if encode_progress_cb:
                        encode_progress_cb((_idx + pct / 100.0) / n_files * 100.0)

                try:
                    audio_io.encode_with_ffmpeg(wav_path, out_path, codec=codec, bitrate=bitrate,
                                                 progress_cb=_file_progress if encode_progress_cb else None,
                                                 duration=duration)
                except Exception:
                    if os.path.exists(out_path):
                        os.remove(out_path)
                    raise
                finally:
                    if os.path.exists(wav_path):
                        os.remove(wav_path)
                outputs.append(out_path)

    return outputs


def ffmpeg_pan_filter(channels, mode):
    """Genera el filtro 'pan' de ffmpeg equivalente a las ganancias actuales."""

    parts = []
    for c in channels:
        factor = 10 ** (c.gain_db / 20.0)
        parts.append(f"{c.pan}={factor:.4f}*{c.pan}")
    layout = {'5.1': '5.1', 'stereo': 'stereo', 'mono': 'mono'}[mode]
    if mode == 'mono':
        g = channels[0].gain_db
        sign = '+' if g >= 0 else ''
        return f"volume={sign}{g:.1f}dB"
    return f"pan={layout}|" + "|".join(parts)
