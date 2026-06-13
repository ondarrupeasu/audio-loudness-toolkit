"""workers.py — Hilos de fondo para no bloquear la UI durante el análisis."""

from PySide6.QtCore import QThread, Signal

from core.analysis import load_channel_file, analyze_channel


class AnalyzeWorker(QThread):
    """Carga un archivo y analiza el canal en segundo plano."""

    progress = Signal(str)          # etapa actual: 'cargando' | 'true_peak' | 'loudness' | 'done'
    finished_ok = Signal(int)        # índice de canal
    finished_err = Signal(int, str)  # índice de canal, mensaje de error

    def __init__(self, channel, idx, path, true_peak_mode='precise', parent=None):
        super().__init__(parent)
        self.channel = channel
        self.idx = idx
        self.path = path
        self.true_peak_mode = true_peak_mode

    def run(self):
        try:
            self.progress.emit('cargando')
            load_channel_file(self.channel, self.path)
            analyze_channel(
                self.channel,
                true_peak_mode=self.true_peak_mode,
                progress_cb=lambda stage: self.progress.emit(stage),
            )
            self.finished_ok.emit(self.idx)
        except Exception as exc:
            self.finished_err.emit(self.idx, str(exc))


class ExportWorker(QThread):
    """Exporta el máster en segundo plano, con progreso por canal y de codificación."""

    progress = Signal(str, int, int)  # etiqueta de canal, índice, total (fase de preparación)
    encode_progress = Signal(int)     # 0-100, progreso real de ffmpeg durante la codificación
    finished_ok = Signal(list)
    finished_err = Signal(str)

    def __init__(self, channels, mode, out_dir, base_name, file_format, combined, parent=None):
        super().__init__(parent)
        self.channels = channels
        self.mode = mode
        self.out_dir = out_dir
        self.base_name = base_name
        self.file_format = file_format
        self.combined = combined

    def run(self):
        from core.analysis import export_master
        total = len(self.channels)
        counter = {'i': 0}

        def progress_cb(label):
            counter['i'] += 1
            self.progress.emit(label, counter['i'], total)

        def encode_cb(pct):
            self.encode_progress.emit(int(pct))

        try:
            outputs = export_master(
                self.channels, self.mode, self.out_dir, self.base_name,
                file_format=self.file_format, combined=self.combined,
                progress_cb=progress_cb, encode_progress_cb=encode_cb,
            )
            self.finished_ok.emit(outputs)
        except Exception as exc:
            self.finished_err.emit(str(exc))


class StereoSplitWorker(QThread):
    """Decodifica un archivo estéreo y analiza ambos canales (L y R) en segundo plano."""

    progress = Signal(str)
    finished_ok = Signal()
    finished_err = Signal(str)

    def __init__(self, channel_l, channel_r, path, true_peak_mode='precise', parent=None):
        super().__init__(parent)
        self.channel_l = channel_l
        self.channel_r = channel_r
        self.path = path
        self.true_peak_mode = true_peak_mode

    def run(self):
        from core.analysis import load_stereo_split, analyze_channel as _analyze
        try:
            self.progress.emit('cargando')
            mono_l, mono_r, rate = load_stereo_split(self.path)

            self.channel_l.reset()
            self.channel_l.file_path = self.path + ' (canal L)'
            self.channel_l.data = mono_l
            self.channel_l.rate = rate
            self.channel_l.duration = mono_l.shape[0] / rate

            self.channel_r.reset()
            self.channel_r.file_path = self.path + ' (canal R)'
            self.channel_r.data = mono_r
            self.channel_r.rate = rate
            self.channel_r.duration = mono_r.shape[0] / rate

            for ch in (self.channel_l, self.channel_r):
                _analyze(ch, true_peak_mode=self.true_peak_mode,
                         progress_cb=lambda stage: self.progress.emit(stage))

            self.finished_ok.emit()
        except Exception as exc:
            self.finished_err.emit(str(exc))
