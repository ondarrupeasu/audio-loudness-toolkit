"""Worker adicional: recálculo de true peak en segundo plano."""

from PySide6.QtCore import QThread, Signal
from core.analysis import recompute_true_peak


class RecomputeTPWorker(QThread):
    finished_ok = Signal(int)
    finished_err = Signal(int, str)

    def __init__(self, channel, idx, mode, parent=None):
        super().__init__(parent)
        self.channel = channel
        self.idx = idx
        self.mode = mode

    def run(self):
        try:
            recompute_true_peak(self.channel, self.mode)
            self.finished_ok.emit(self.idx)
        except Exception as exc:
            self.finished_err.emit(self.idx, str(exc))
