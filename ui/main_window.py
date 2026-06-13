"""main_window.py — Ventana principal: tiras de canal, panel de loudness, exportación."""

import os
import numpy as np

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QDoubleSpinBox, QFileDialog,
    QGroupBox, QTableWidget, QTableWidgetItem, QLineEdit,
    QHeaderView, QMessageBox, QSizePolicy, QProgressBar, QApplication,
    QScrollArea, QFrame, QAbstractSpinBox,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QClipboard, QFontMetrics

from core.analysis import (
    make_channels, integrated_lufs, normalize_main_channels,
    ffmpeg_pan_filter, export_master, MODE_CONFIGS,
)
from ui.widgets import MeterBar, SignedDoubleSpinBox
from ui.player import PlayerWidget, HAS_SOUNDDEVICE
from ui.workers import AnalyzeWorker, StereoSplitWorker, ExportWorker
from ui.tp_worker import RecomputeTPWorker
from ui.i18n import i18n
from ui.standards_dialog import StandardsDialog


FORMAT_KEYS = ['wav', 'flac', 'aac', 'ac3', 'eac3', 'mp3']

STAGE_KEYS = {
    'cargando': 'stage_loading',
    'true_peak': 'stage_true_peak',
    'loudness': 'stage_loudness',
    'done': 'stage_done',
}
STAGE_PCT = {'cargando': 10, 'true_peak': 45, 'loudness': 80, 'done': 100}

WINDOW_SIZE = {
    '5.1': (1500, 700),
    'stereo': (1000, 700),
    'mono': (820, 700),
}


class ChannelStrip(QWidget):
    """Tira de un canal: carga, medidores, fader de ganancia, reproducción."""

    def __init__(self, channel, on_load, on_gain_change, parent=None):
        super().__init__(parent)
        self.channel = channel
        self._on_gain_change = on_gain_change

        self.setMinimumWidth(150)
        self.setMaximumWidth(220)

        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        self.head = QLabel(f"<b style='font-size:18px'>{channel.label}</b>")
        self.head.setAlignment(Qt.AlignCenter)
        self.sub = QLabel(i18n.tr(channel.name))
        self.sub.setAlignment(Qt.AlignCenter)
        self.sub.setStyleSheet("color: #93908a; font-size: 10px; text-transform: uppercase;")
        layout.addWidget(self.head)
        layout.addWidget(self.sub)

        self.load_btn = QPushButton(i18n.tr('load_file'))
        self.load_btn.clicked.connect(on_load)
        layout.addWidget(self.load_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.fname_label = QLabel("")
        self.fname_label.setWordWrap(True)
        self.fname_label.setStyleSheet("color: #93908a; font-size: 10px;")
        layout.addWidget(self.fname_label)

        self.peak_label = QLabel("")
        self.peak_bar = MeterBar('peak')
        self.rms_label = QLabel("")
        self.rms_bar = MeterBar('peak')
        self.tp_label = QLabel("")
        self.tp_bar = MeterBar('tp')
        for lab, bar in [(self.peak_label, self.peak_bar),
                         (self.rms_label, self.rms_bar),
                         (self.tp_label, self.tp_bar)]:
            lab.setStyleSheet("font-family: monospace; font-size: 11px;")
            layout.addWidget(lab)
            layout.addWidget(bar)
        self._set_empty_meter_labels()

        # control de ganancia: spinbox + botones -/+ propios (más visibles que
        # las flechas nativas) + reset, todo en una fila compacta
        gain_row = QHBoxLayout()
        gain_row.setSpacing(2)

        self.gain_down_btn = QPushButton("−")
        self.gain_down_btn.setFixedWidth(26)
        self.gain_down_btn.setEnabled(False)
        self.gain_down_btn.clicked.connect(lambda: self.gain_spin.stepBy(-1))
        gain_row.addWidget(self.gain_down_btn)

        self.gain_spin = SignedDoubleSpinBox()
        self.gain_spin.setRange(-24.0, 12.0)
        self.gain_spin.setSingleStep(0.1)
        self.gain_spin.setDecimals(1)
        self.gain_spin.setSuffix(" dB")
        self.gain_spin.setAlignment(Qt.AlignCenter)
        self.gain_spin.setMinimumHeight(28)
        self.gain_spin.setEnabled(False)
        self.gain_spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.gain_spin.setStyleSheet("font-family: monospace; font-weight: bold;")
        self.gain_spin.valueChanged.connect(self._on_spin_changed)
        gain_row.addWidget(self.gain_spin, 1)

        self.gain_up_btn = QPushButton("+")
        self.gain_up_btn.setFixedWidth(26)
        self.gain_up_btn.setEnabled(False)
        self.gain_up_btn.clicked.connect(lambda: self.gain_spin.stepBy(1))
        gain_row.addWidget(self.gain_up_btn)

        layout.addLayout(gain_row)

        self.reset_btn = QPushButton(i18n.tr('reset'))
        self.reset_btn.setEnabled(False)
        self.reset_btn.clicked.connect(lambda: self.gain_spin.setValue(0.0))
        layout.addWidget(self.reset_btn)

        self.player = PlayerWidget(gain_provider=lambda: self.channel.gain_db)
        layout.addWidget(self.player)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #93908a; font-size: 10px;")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        layout.addStretch()

    def _set_empty_meter_labels(self):
        self.peak_label.setText(i18n.tr('peak_empty'))
        self.rms_label.setText(i18n.tr('rms_empty'))
        self.tp_label.setText(i18n.tr('tp_empty'))

    def _on_spin_changed(self, value):
        self.channel.gain_db = value
        self.refresh_meters()
        self._on_gain_change()

    def set_gain_db(self, gain_db):
        self.gain_spin.blockSignals(True)
        self.gain_spin.setValue(gain_db)
        self.gain_spin.blockSignals(False)
        self.channel.gain_db = gain_db
        self.refresh_meters()

    def refresh_meters(self):
        ch = self.channel
        if not ch.loaded or ch.peak_db is None:
            self._set_empty_meter_labels()
            return
        peak = ch.display_peak_db()
        rms = ch.display_rms_db()
        tp = ch.display_true_peak_db()
        self.peak_label.setText(i18n.tr('peak_value', v=peak))
        self.rms_label.setText(i18n.tr('rms_value', v=rms))
        self.tp_label.setText(i18n.tr('tp_value', v=tp))
        self.peak_bar.set_db(peak)
        self.rms_bar.set_db(rms)
        self.tp_bar.set_db(tp)

    def set_progress(self, pct, visible=True):
        self.progress_bar.setVisible(visible)
        self.progress_bar.setValue(pct)

    def on_loaded(self):
        ch = self.channel
        name = os.path.basename(str(ch.file_path)) if ch.file_path else ""
        self.fname_label.setText(name)
        self.fname_label.setToolTip(str(ch.file_path) if ch.file_path else "")
        self.gain_spin.setEnabled(True)
        self.gain_down_btn.setEnabled(True)
        self.gain_up_btn.setEnabled(True)
        self.reset_btn.setEnabled(True)
        if ch.duration:
            self.status_label.setText(i18n.tr('rate_duration', rate=ch.rate, dur=ch.duration))
        self.refresh_meters()
        self.player.set_audio(ch.data, ch.rate)
        self.set_progress(0, visible=False)

    def retranslate(self):
        self.sub.setText(i18n.tr(self.channel.name))
        self.load_btn.setText(i18n.tr('load_file'))
        self.reset_btn.setText(i18n.tr('reset'))
        self.refresh_meters()
        self.player.retranslate()
        if self.channel.loaded and self.channel.duration:
            self.status_label.setText(i18n.tr('rate_duration', rate=self.channel.rate, dur=self.channel.duration))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(*WINDOW_SIZE['5.1'])

        self.mode = '5.1'
        self.true_peak_mode = 'precise'
        self.channels = make_channels(self.mode)
        self.strips = []
        self.workers = []  # mantener referencias vivas

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        # --- barra superior: modo + true peak + idioma + leyenda ---
        top = QHBoxLayout()
        self.mode_label = QLabel()
        top.addWidget(self.mode_label)
        self.mode_combo = QComboBox()
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        top.addWidget(self.mode_combo)

        self.tp_label = QLabel()
        top.addWidget(self.tp_label)
        self.tp_combo = QComboBox()
        self.tp_combo.currentIndexChanged.connect(self._on_tp_mode_changed)
        top.addWidget(self.tp_combo)

        self.lang_label = QLabel()
        top.addWidget(self.lang_label)
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("Español", 'es')
        self.lang_combo.addItem("English", 'en')
        self._size_combo(self.lang_combo, ["Español", "English"])
        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        top.addWidget(self.lang_combo)

        top.addStretch()
        self.legend_label = QLabel()
        self.legend_label.setStyleSheet("font-size: 11px; color: #93908a;")
        top.addWidget(self.legend_label)
        root.addLayout(top)

        # --- tiras de canal (con scroll horizontal si la ventana es estrecha) ---
        self.strips_container = QWidget()
        self.strips_layout = QHBoxLayout(self.strips_container)
        self.strips_layout.setContentsMargins(0, 0, 0, 0)
        strips_scroll = QScrollArea()
        strips_scroll.setWidget(self.strips_container)
        strips_scroll.setWidgetResizable(True)
        strips_scroll.setFrameShape(QFrame.NoFrame)
        strips_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        strips_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        root.addWidget(strips_scroll)
        self._rebuild_strips()

        # --- panel global ---
        global_row = QHBoxLayout()

        self.loud_box = QGroupBox()
        self.loud_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        loud_layout = QVBoxLayout(self.loud_box)
        lufs_row = QHBoxLayout()
        self.lufs_label = QLabel()
        self.lufs_label.setStyleSheet("font-family: monospace; font-size: 28px; font-weight: bold;")
        lufs_row.addWidget(self.lufs_label)
        lufs_row.addStretch()
        self.standards_btn = QPushButton()
        self.standards_btn.clicked.connect(self._show_standards)
        lufs_row.addWidget(self.standards_btn, 0, Qt.AlignTop)
        loud_layout.addLayout(lufs_row)
        self.delta_label = QLabel("")
        loud_layout.addWidget(self.delta_label)

        controls_grid = QGridLayout()
        controls_grid.setColumnStretch(1, 1)
        controls_grid.setColumnStretch(2, 1)

        # fila 0: target loudness + normalizar
        self.target_label = QLabel()
        controls_grid.addWidget(self.target_label, 0, 0)

        target_group = QWidget()
        target_group_layout = QHBoxLayout(target_group)
        target_group_layout.setContentsMargins(0, 0, 0, 0)
        target_group_layout.setSpacing(2)

        self.target_spin = SignedDoubleSpinBox()
        self.target_spin.setRange(-60, 0)
        self.target_spin.setValue(-23.0)
        self.target_spin.setSingleStep(0.5)
        self.target_spin.setDecimals(1)
        self.target_spin.setMaximumWidth(70)
        self.target_spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.target_spin.valueChanged.connect(self._update_global)

        self.target_down_btn = QPushButton("−")
        self.target_down_btn.setFixedWidth(26)
        self.target_down_btn.clicked.connect(lambda: self.target_spin.stepBy(-1))
        self.target_up_btn = QPushButton("+")
        self.target_up_btn.setFixedWidth(26)
        self.target_up_btn.clicked.connect(lambda: self.target_spin.stepBy(1))

        target_group_layout.addWidget(self.target_down_btn)
        target_group_layout.addWidget(self.target_spin)
        target_group_layout.addWidget(self.target_up_btn)
        target_group_layout.addStretch()
        controls_grid.addWidget(target_group, 0, 1)

        self.normalize_btn = QPushButton()
        self.normalize_btn.clicked.connect(self._on_normalize)
        controls_grid.addWidget(self.normalize_btn, 0, 2)

        # fila 1: compensación LFE (mismas columnas -> mismo ancho)
        self.lfe_label = QLabel()
        controls_grid.addWidget(self.lfe_label, 1, 0)
        self.lfe_minus10_btn = QPushButton()
        self.lfe_minus10_btn.clicked.connect(self._on_lfe_minus10)
        controls_grid.addWidget(self.lfe_minus10_btn, 1, 1)
        self.lfe_reset_btn = QPushButton()
        self.lfe_reset_btn.clicked.connect(self._on_lfe_reset)
        controls_grid.addWidget(self.lfe_reset_btn, 1, 2)

        loud_layout.addLayout(controls_grid)
        self.lfe_widgets = [self.lfe_label, self.lfe_minus10_btn, self.lfe_reset_btn]

        self.global_status = QLabel("")
        self.global_status.setWordWrap(True)
        self.global_status.setStyleSheet("color: #d4564a;")
        loud_layout.addWidget(self.global_status)

        # --- filtro ffmpeg (en la misma columna que el panel de loudness,
        #     que tiene espacio libre debajo) ---
        self.ffmpeg_box = QGroupBox()
        self.ffmpeg_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        ffmpeg_layout = QHBoxLayout(self.ffmpeg_box)
        self.ffmpeg_line = QLineEdit()
        self.ffmpeg_line.setReadOnly(True)
        self.ffmpeg_line.setStyleSheet("font-family: monospace;")
        ffmpeg_layout.addWidget(self.ffmpeg_line)
        self.copy_btn = QPushButton()
        self.copy_btn.clicked.connect(self._copy_filter)
        ffmpeg_layout.addWidget(self.copy_btn)

        left_col = QVBoxLayout()
        left_col.addWidget(self.loud_box)
        left_col.addWidget(self.ffmpeg_box)
        global_row.addLayout(left_col, 1)

        # --- resumen ---
        self.summary_box = QGroupBox()
        summary_layout = QVBoxLayout(self.summary_box)
        self.summary_table = QTableWidget(0, 4)
        self.summary_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.summary_table.verticalHeader().setVisible(False)
        self.summary_table.setEditTriggers(QTableWidget.NoEditTriggers)
        summary_layout.addWidget(self.summary_table)
        summary_layout.addStretch()
        global_row.addWidget(self.summary_box, 1)

        root.addLayout(global_row)

        # --- exportación ---
        self.export_box = QGroupBox()
        export_layout = QHBoxLayout(self.export_box)
        self.format_label = QLabel()
        export_layout.addWidget(self.format_label)
        self.format_combo = QComboBox()
        export_layout.addWidget(self.format_combo)

        self.export_mode_label = QLabel()
        export_layout.addWidget(self.export_mode_label)
        self.export_mode_combo = QComboBox()
        export_layout.addWidget(self.export_mode_combo)

        self.basename_label = QLabel()
        export_layout.addWidget(self.basename_label)
        self.basename_edit = QLineEdit("master")
        self.basename_edit.setMaximumWidth(120)
        export_layout.addWidget(self.basename_edit)

        self.export_btn = QPushButton()
        self.export_btn.clicked.connect(self._on_export)
        export_layout.addWidget(self.export_btn)

        self.export_status = QLabel("")
        self.export_status.setWordWrap(True)
        export_layout.addWidget(self.export_status, 1)
        root.addWidget(self.export_box)

        self.export_progress = QProgressBar()
        self.export_progress.setRange(0, 100)
        self.export_progress.setTextVisible(True)
        self.export_progress.setFormat("%p%")
        self.export_progress.setVisible(False)
        root.addWidget(self.export_progress)

        self.retranslate_ui()
        self._fit_to_content()
        QTimer.singleShot(0, self._fit_summary_table)

    def _fit_to_content(self):
        """Abre la ventana lo bastante grande para que se vea todo de una vez,
        sin exceder el área disponible de la pantalla."""
        target_w, target_h = WINDOW_SIZE.get(self.mode, WINDOW_SIZE['5.1'])
        hint = self.centralWidget().sizeHint()
        w, h = max(target_w, hint.width()), max(target_h, hint.height())

        screen = self.screen() or QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            w = min(w, avail.width())
            h = min(h, avail.height())

        self.resize(w, h)

    # ------------------------------------------------------------------
    def _size_combo(self, combo, texts):
        fm = QFontMetrics(combo.font())
        max_text = max(texts, key=len, default="")
        combo.setMinimumContentsLength(len(max_text))
        combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        combo.view().setMinimumWidth(fm.horizontalAdvance(max_text) + 40)

    def _retranslate_combo(self, combo, items):
        """items: lista de (data, label). Conserva la selección actual por 'data'."""
        current_data = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        for data, label in items:
            combo.addItem(label, data)
        if current_data is not None:
            idx = combo.findData(current_data)
            if idx >= 0:
                combo.setCurrentIndex(idx)
        combo.blockSignals(False)

        # evitar que el texto se recorte tanto en el combo cerrado como en la lista
        self._size_combo(combo, [it[1] for it in items])

    def retranslate_ui(self):
        self.setWindowTitle(i18n.tr('window_title'))

        self.mode_label.setText(i18n.tr('mode_label'))
        self._retranslate_combo(self.mode_combo, [
            ('5.1', i18n.tr('mode_51')),
            ('stereo', i18n.tr('mode_stereo')),
            ('mono', i18n.tr('mode_mono')),
        ])

        self.tp_label.setText(i18n.tr('tp_label'))
        self._retranslate_combo(self.tp_combo, [
            ('precise', i18n.tr('tp_precise')),
            ('fast', i18n.tr('tp_fast')),
        ])

        self.lang_label.setText(i18n.tr('lang_label'))

        self.legend_label.setText(
            f"<span style='color:#5fbe8a'>\u25cf</span> {i18n.tr('legend_ok')}&nbsp;&nbsp;"
            f"<span style='color:#e8a23c'>\u25cf</span> {i18n.tr('legend_warn')}&nbsp;&nbsp;"
            f"<span style='color:#d4564a'>\u25cf</span> {i18n.tr('legend_danger')}"
        )

        self.loud_box.setTitle(i18n.tr('loudness_box'))
        self.standards_btn.setText(i18n.tr('standards_btn'))
        self.lufs_label.setToolTip(i18n.tr('lufs_tooltip'))
        self.target_label.setText(i18n.tr('target_label'))
        self.target_label.setToolTip(i18n.tr('target_tooltip'))
        self.target_spin.setToolTip(i18n.tr('target_tooltip'))
        self.lfe_label.setText(i18n.tr('lfe_comp_label'))
        self.lfe_minus10_btn.setText(i18n.tr('lfe_minus10'))
        self.lfe_reset_btn.setText(i18n.tr('lfe_reset'))

        self.summary_box.setTitle(i18n.tr('summary_box'))
        self.summary_table.setHorizontalHeaderLabels([
            i18n.tr('col_channel'), i18n.tr('col_gain'),
            i18n.tr('col_peak_final'), i18n.tr('col_tp_final'),
        ])

        self.ffmpeg_box.setTitle(i18n.tr('ffmpeg_box'))
        self.copy_btn.setText(i18n.tr('copy'))

        self.export_box.setTitle(i18n.tr('export_box'))
        self.format_label.setText(i18n.tr('format_label'))
        self._retranslate_combo(self.format_combo, [(k, i18n.tr(f'fmt_{k}')) for k in FORMAT_KEYS])
        self.export_mode_label.setText(i18n.tr('export_mode_label'))
        self._retranslate_combo(self.export_mode_combo, [
            (True, i18n.tr('export_combined')),
            (False, i18n.tr('export_separate')),
        ])
        self.basename_label.setText(i18n.tr('basename_label'))
        self.export_btn.setText(i18n.tr('export_button'))

        self._update_lfe_visibility()

        for strip in self.strips:
            strip.retranslate()

        self._update_global()

    def _on_lang_changed(self, _index):
        lang = self.lang_combo.currentData()
        i18n.set_lang(lang)
        self.retranslate_ui()

    # ------------------------------------------------------------------
    def _rebuild_strips(self):
        for s in self.strips:
            self.strips_layout.removeWidget(s)
            s.deleteLater()
        self.strips = []
        self.channels = make_channels(self.mode)

        for idx, ch in enumerate(self.channels):
            strip = ChannelStrip(
                ch,
                on_load=lambda checked=False, i=idx: self._on_load_clicked(i),
                on_gain_change=self._update_global,
            )
            self.strips.append(strip)
            self.strips_layout.addWidget(strip)

        # ancho mínimo para que cada tira tenga su espacio antes de activar el scroll
        self.strips_container.setMinimumWidth(len(self.channels) * 158)

    def _on_mode_changed(self, _index):
        self.mode = self.mode_combo.currentData()
        self.workers.clear()
        self._rebuild_strips()
        self._update_lfe_visibility()
        self.global_status.setText("")
        self.export_status.setText("")
        self._update_global()

        target_w, target_h = WINDOW_SIZE.get(self.mode, WINDOW_SIZE['5.1'])
        new_w = max(self.width(), target_w)
        new_h = max(self.height(), target_h)
        if (new_w, new_h) != (self.width(), self.height()):
            self.resize(new_w, new_h)

    def _update_lfe_visibility(self):
        visible = self.mode == '5.1'
        for w in self.lfe_widgets:
            w.setVisible(visible)
        self.normalize_btn.setText(
            i18n.tr('normalize_main') if self.mode == '5.1' else i18n.tr('normalize')
        )

    # ------------------------------------------------------------------
    def _on_load_clicked(self, idx):
        path, _ = QFileDialog.getOpenFileName(
            self, i18n.tr('dialog_load_audio'), "",
            "Audio (*.wav *.aif *.aiff *.flac *.mp3 *.aac *.m4a *.ogg);;Todos (*)"
        )
        if not path:
            return

        if self.mode == 'stereo':
            try:
                from core.io import probe_audio
                info = probe_audio(path)
            except Exception as exc:
                QMessageBox.warning(self, i18n.tr('dialog_error'), str(exc))
                return
            if info['channels'] >= 2:
                self._load_stereo_split(path)
                return

        strip = self.strips[idx]
        strip.set_progress(0, visible=True)
        strip.status_label.setText(i18n.tr(STAGE_KEYS['cargando']))
        worker = AnalyzeWorker(self.channels[idx], idx, path, true_peak_mode=self.true_peak_mode)
        worker.progress.connect(lambda stage, s=strip: self._on_analyze_progress(s, stage))
        worker.finished_ok.connect(self._on_analyze_done)
        worker.finished_err.connect(self._on_analyze_error)
        self.workers.append(worker)
        worker.start()

    def _on_analyze_progress(self, strip, stage):
        pct = STAGE_PCT.get(stage, 0)
        strip.set_progress(pct, visible=(stage != 'done'))
        strip.status_label.setText(i18n.tr(STAGE_KEYS.get(stage, stage)))

    def _load_stereo_split(self, path):
        for s in self.strips:
            s.set_progress(0, visible=True)
            s.status_label.setText(i18n.tr(STAGE_KEYS['cargando']))
        worker = StereoSplitWorker(self.channels[0], self.channels[1], path,
                                    true_peak_mode=self.true_peak_mode)
        worker.progress.connect(lambda stage: [self._on_analyze_progress(s, stage) for s in self.strips])
        worker.finished_ok.connect(self._on_stereo_done)
        worker.finished_err.connect(lambda msg: QMessageBox.warning(self, i18n.tr('dialog_error'), msg))
        self.workers.append(worker)
        worker.start()

    def _on_analyze_done(self, idx):
        self.strips[idx].on_loaded()
        self._update_global()

    def _on_stereo_done(self):
        for strip in self.strips:
            strip.on_loaded()
        self._update_global()

    def _on_analyze_error(self, idx, msg):
        self.strips[idx].set_progress(0, visible=False)
        self.strips[idx].status_label.setText(i18n.tr('error_prefix', msg=msg))

    def _on_tp_mode_changed(self, _index):
        new_mode = self.tp_combo.currentData()
        if new_mode == self.true_peak_mode:
            return
        self.true_peak_mode = new_mode
        for idx, ch in enumerate(self.channels):
            if ch.loaded:
                strip = self.strips[idx]
                strip.set_progress(0, visible=True)
                strip.progress_bar.setRange(0, 0)  # indeterminado
                strip.status_label.setText(i18n.tr('stage_recompute_tp'))
                worker = RecomputeTPWorker(ch, idx, new_mode)
                worker.finished_ok.connect(self._on_tp_recomputed)
                self.workers.append(worker)
                worker.start()

    def _on_tp_recomputed(self, idx):
        strip = self.strips[idx]
        strip.progress_bar.setRange(0, 100)
        strip.set_progress(0, visible=False)
        strip.refresh_meters()
        if strip.channel.duration:
            strip.status_label.setText(i18n.tr('rate_duration', rate=strip.channel.rate, dur=strip.channel.duration))
        self._update_global()

    # ------------------------------------------------------------------
    def _update_global(self):
        lufs = integrated_lufs(self.channels)
        if lufs is None:
            self.lufs_label.setText(i18n.tr('lufs_empty'))
            self.delta_label.setText("")
        else:
            self.lufs_label.setText(i18n.tr('lufs_value', v=lufs))
            target = self.target_spin.value()
            delta = lufs - target
            self.delta_label.setText(i18n.tr('lu_vs_target', v=delta))

        # tabla resumen
        self.summary_table.setRowCount(len(self.channels))
        for row, ch in enumerate(self.channels):
            self.summary_table.setItem(row, 0, QTableWidgetItem(ch.label))
            gain_str = i18n.tr('gain_value', v=ch.gain_db) if ch.loaded else i18n.tr('dash')
            self.summary_table.setItem(row, 1, QTableWidgetItem(gain_str))
            if ch.loaded and ch.peak_db is not None:
                self.summary_table.setItem(row, 2, QTableWidgetItem(f"{ch.display_peak_db():.1f}"))
                self.summary_table.setItem(row, 3, QTableWidgetItem(f"{ch.display_true_peak_db():.1f}"))
            else:
                self.summary_table.setItem(row, 2, QTableWidgetItem(i18n.tr('dash')))
                self.summary_table.setItem(row, 3, QTableWidgetItem(i18n.tr('dash')))

        self.ffmpeg_line.setText(ffmpeg_pan_filter(self.channels, self.mode))
        self._fit_summary_table()

    def _fit_summary_table(self):
        t = self.summary_table
        t.resizeRowsToContents()
        rows_h = sum(t.rowHeight(r) for r in range(t.rowCount()))
        header_h = t.horizontalHeader().height()
        frame = 2 * t.frameWidth()
        h = header_h + rows_h + frame + 4  # pequeño margen de seguridad
        t.setMinimumHeight(h)
        t.setMaximumHeight(h)

    def _on_normalize(self):
        target = self.target_spin.value()
        delta, limited, resulting = normalize_main_channels(self.channels, target)
        if delta is None:
            return
        for strip in self.strips:
            strip.set_gain_db(strip.channel.gain_db)
        if limited:
            self.global_status.setText(i18n.tr('normalize_limited', delta=delta, result=resulting, target=target))
        else:
            self.global_status.setText("")
        self._update_global()

    def _on_lfe_minus10(self):
        idx = next((i for i, c in enumerate(self.channels) if c.key == 'LFE'), None)
        if idx is None or not self.channels[idx].loaded:
            return
        strip = self.strips[idx]
        new_gain = max(-24.0, self.channels[idx].gain_db - 10.0)
        strip.set_gain_db(new_gain)
        self._update_global()

    def _on_lfe_reset(self):
        idx = next((i for i, c in enumerate(self.channels) if c.key == 'LFE'), None)
        if idx is None:
            return
        self.strips[idx].set_gain_db(0.0)
        self._update_global()

    def _copy_filter(self):
        QApplication.clipboard().setText(self.ffmpeg_line.text())

    def _show_standards(self):
        dlg = StandardsDialog(self)
        dlg.exec()

    # ------------------------------------------------------------------
    def _on_export(self):
        loaded = [c for c in self.channels if c.loaded]
        if not loaded:
            self.export_status.setText(i18n.tr('export_need_channel'))
            return

        out_dir = QFileDialog.getExistingDirectory(self, i18n.tr('dialog_out_dir'))
        if not out_dir:
            return

        fmt = self.format_combo.currentData()
        combined = self.export_mode_combo.currentData()
        base_name = self.basename_edit.text().strip() or "master"

        self.export_btn.setEnabled(False)
        self.export_status.setText(i18n.tr('exporting'))
        self.export_progress.setVisible(True)
        self.export_progress.setValue(0)

        worker = ExportWorker(self.channels, self.mode, out_dir, base_name,
                               file_format=fmt, combined=combined)
        worker.progress.connect(self._on_export_progress)
        worker.encode_progress.connect(self._on_encode_progress)
        worker.finished_ok.connect(self._on_export_done)
        worker.finished_err.connect(self._on_export_error)
        self.workers.append(worker)
        worker.start()

    def _on_export_progress(self, label, idx, total):
        pct = int(idx / total * 100) if total else 0
        self.export_progress.setValue(pct)
        self.export_status.setText(i18n.tr('exporting_progress', label=label, idx=idx, total=total))

    def _on_encode_progress(self, pct):
        self.export_progress.setValue(pct)
        fmt = self.format_combo.currentData().upper()
        self.export_status.setText(i18n.tr('exporting_encode', fmt=fmt, pct=pct))

    def _on_export_done(self, outputs):
        self.export_progress.setValue(100)
        self.export_progress.setVisible(False)
        self.export_btn.setEnabled(True)
        files = ", ".join(os.path.basename(p) for p in outputs)
        self.export_status.setText(i18n.tr('exported', files=files))

    def _on_export_error(self, msg):
        self.export_progress.setVisible(False)
        self.export_btn.setEnabled(True)
        self.export_status.setText(i18n.tr('export_error', msg=msg))
