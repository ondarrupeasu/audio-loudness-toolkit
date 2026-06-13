"""player.py — Reproducción con barra de progreso y salto a cualquier punto."""

import numpy as np
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QSlider, QLabel
from PySide6.QtCore import Qt, QTimer

from ui.i18n import i18n

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except Exception:
    HAS_SOUNDDEVICE = False


def _fmt_time(seconds):
    seconds = max(0, int(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


class PlayerWidget(QWidget):
    """Reproduce un array mono con control de posición. La ganancia se
    consulta en vivo mediante gain_provider() (callable -> dB)."""

    def __init__(self, gain_provider=None, parent=None):
        super().__init__(parent)
        self.gain_provider = gain_provider or (lambda: 0.0)
        self.data = None
        self.rate = None
        self.pos = 0
        self.stream = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        row = QHBoxLayout()
        self.play_btn = QPushButton(i18n.tr('play'))
        self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self._toggle)
        row.addWidget(self.play_btn)
        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setStyleSheet("font-family: monospace; font-size: 10px;")
        row.addWidget(self.time_label)
        layout.addLayout(row)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.setEnabled(False)
        self.slider.sliderMoved.connect(self._on_seek)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 3px;
                background: #383c40;
                border-radius: 1px;
            }
            QSlider::sub-page:horizontal {
                background: #6b6f73;
                border-radius: 1px;
            }
            QSlider::handle:horizontal {
                width: 8px;
                height: 8px;
                margin: -3px 0;
                background: #d9854a;
                border-radius: 4px;
            }
            QSlider::handle:horizontal:disabled {
                background: #4a4d50;
            }
        """)
        layout.addWidget(self.slider)

        if not HAS_SOUNDDEVICE:
            self.play_btn.setToolTip(i18n.tr('play_tooltip_unavailable'))

        self.timer = QTimer(self)
        self.timer.setInterval(150)
        self.timer.timeout.connect(self._tick)

    def set_audio(self, data, rate):
        self._stop()
        self.data = data
        self.rate = rate
        self.pos = 0
        enabled = HAS_SOUNDDEVICE and data is not None and rate is not None
        self.play_btn.setEnabled(enabled)
        self.slider.setEnabled(enabled)
        self.slider.setValue(0)
        self._update_time_label()

    def _toggle(self):
        if self.stream is not None:
            self._stop()
        else:
            self._play()

    def _play(self):
        if not HAS_SOUNDDEVICE or self.data is None:
            return
        if self.pos >= len(self.data):
            self.pos = 0

        def callback(outdata, frames, time_info, status):
            chunk = self.data[self.pos:self.pos + frames]
            n = len(chunk)
            factor = 10 ** (self.gain_provider() / 20.0)
            outdata[:n, 0] = chunk * factor
            if n < frames:
                outdata[n:, 0] = 0
                self.pos += n
                raise sd.CallbackStop()
            self.pos += frames

        self.stream = sd.OutputStream(
            samplerate=self.rate, channels=1, dtype='float32',
            blocksize=2048, callback=callback,
        )
        self.stream.start()
        self.play_btn.setText(i18n.tr('play_stop'))
        self.timer.start()

    def _stop(self):
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
        self.play_btn.setText(i18n.tr('play'))
        self.timer.stop()

    def _tick(self):
        if self.stream is None or not self.stream.active:
            self._stop()
            return
        if self.data is not None and len(self.data) > 0:
            pct = int(self.pos / len(self.data) * 1000)
            self.slider.blockSignals(True)
            self.slider.setValue(min(1000, pct))
            self.slider.blockSignals(False)
        self._update_time_label()
        if self.pos >= len(self.data):
            self._stop()
            self.pos = 0
            self.slider.setValue(0)
            self._update_time_label()

    def _on_seek(self, value):
        if self.data is None or self.rate is None:
            return
        self.pos = int(value / 1000 * len(self.data))
        self._update_time_label()

    def _update_time_label(self):
        if self.data is None or self.rate is None:
            self.time_label.setText("0:00 / 0:00")
            return
        cur = self.pos / self.rate
        total = len(self.data) / self.rate
        self.time_label.setText(f"{_fmt_time(cur)} / {_fmt_time(total)}")

    def retranslate(self):
        playing = self.stream is not None
        self.play_btn.setText(i18n.tr('play_stop') if playing else i18n.tr('play'))
        if not HAS_SOUNDDEVICE:
            self.play_btn.setToolTip(i18n.tr('play_tooltip_unavailable'))
