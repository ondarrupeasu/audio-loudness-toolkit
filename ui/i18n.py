"""i18n.py — Textos de la interfaz en español e inglés."""

STRINGS = {
    'es': {
        'window_title': 'AudioLoudnessToolkit — 5.1 / Estéreo / Mono',
        'mode_label': 'Modo:',
        'mode_51': '5.1 (6 archivos)',
        'mode_stereo': 'Estéreo',
        'mode_mono': 'Mono',
        'tp_label': 'True peak:',
        'tp_precise': 'Preciso (sobremuestreo x4)',
        'tp_fast': 'Rápido (pico de muestra)',
        'lang_label': 'Idioma:',
        'legend_ok': 'con margen',
        'legend_warn': 'cerca del techo (normal)',
        'legend_danger': 'riesgo de clipping',

        'ch_front_left': 'Front Left',
        'ch_front_right': 'Front Right',
        'ch_center': 'Center',
        'ch_lfe': 'Subwoofer',
        'ch_surround_left': 'Surround Left',
        'ch_surround_right': 'Surround Right',
        'ch_left': 'Left',
        'ch_right': 'Right',
        'ch_mono': 'Mono',

        'load_file': 'Cargar archivo',
        'peak_value': 'Pico: {v:.1f} dBFS',
        'peak_empty': 'Pico: —',
        'rms_value': 'RMS: {v:.1f} dBFS',
        'rms_empty': 'RMS: —',
        'tp_value': 'True Peak: {v:.1f} dBTP',
        'tp_empty': 'True Peak: —',
        'reset': 'Reset',
        'play': '▶ Reproducir',
        'play_stop': '■ Detener',
        'play_tooltip_unavailable': 'sounddevice no disponible',
        'rate_duration': '{rate} Hz · {dur:.1f} s',

        'stage_loading': 'Cargando archivo...',
        'stage_true_peak': 'Calculando true peak...',
        'stage_loudness': 'Calculando loudness...',
        'stage_done': 'Listo',
        'stage_recompute_tp': 'Recalculando true peak...',
        'analyzing': 'Analizando...',
        'error_prefix': 'Error: {msg}',

        'loudness_box': 'Loudness integrado (gateo BS.1770-4 completo)',
        'lufs_empty': '— LUFS',
        'lufs_value': '{v:.1f} LUFS',
        'lu_vs_target': '{v:+.1f} LU vs target',
        'target_label': 'Target (LUFS):',
        'normalize_main': 'Normalizar canales principales',
        'normalize': 'Normalizar',
        'lfe_comp_label': 'Compensación LFE:',
        'lfe_minus10': 'LFE −10 dB (quitar ganancia de sala)',
        'lfe_reset': 'Reset LFE',
        'normalize_limited': (
            'Ajuste limitado a {delta:+.1f} dB para no superar -1 dBTP. '
            'Loudness resultante: {result:.1f} LUFS (target era {target:.1f}).'
        ),

        'summary_box': 'Resumen de ganancias',
        'col_channel': 'Canal',
        'col_gain': 'Ganancia',
        'col_peak_final': 'Pico final',
        'col_tp_final': 'TP final',
        'gain_value': '{v:+.1f} dB',
        'dash': '—',

        'ffmpeg_box': 'Filtro ffmpeg equivalente',
        'copy': 'Copiar',

        'export_box': 'Exportación',
        'format_label': 'Formato:',
        'export_mode_label': 'Modo:',
        'export_combined': 'Interleaved (un archivo)',
        'export_separate': 'Separado (un archivo por canal)',
        'basename_label': 'Nombre base:',
        'export_button': 'Exportar...',
        'export_need_channel': 'Carga al menos un canal antes de exportar.',
        'exporting': 'Exportando...',
        'exporting_progress': 'Preparando... ({label}, {idx}/{total})',
        'exporting_encode': 'Codificando a {fmt}... {pct}%',
        'exported': 'Exportado: {files}',
        'export_error': 'Error al exportar: {msg}',

        'fmt_wav': 'WAV (24-bit PCM)',
        'fmt_flac': 'FLAC',
        'fmt_aac': 'AAC (.m4a)',
        'fmt_ac3': 'AC3 — Dolby Digital (.mp4)',
        'fmt_eac3': 'E-AC3 — Dolby Digital Plus (.mp4)',
        'fmt_mp3': 'MP3 (downmix estéreo si es 5.1)',

        'dialog_error': 'Error',
        'dialog_load_audio': 'Cargar audio',
        'dialog_out_dir': 'Carpeta de destino',

        'standards_btn': 'ⓘ Estándares',
        'standards_title': 'Estándares de loudness y true peak por destino',
        'standards_col_dest': 'Destino',
        'standards_col_lufs': 'LUFS objetivo',
        'standards_col_tp': 'True Peak máx.',
        'standards_col_norm': 'Norma / referencia',
        'close': 'Cerrar',
        'lufs_tooltip': (
            'Loudness integrado de todo el programa (gateo BS.1770-4 completo).\n'
            'Referencias habituales: -23 LUFS (TV UE, EBU R128), -24 LUFS (TV EEUU, ATSC A/85),\n'
            '-27 LUFS (Netflix), -14 a -16 LUFS (streaming/música).\n'
            'Pulsa "Estándares" para ver la tabla completa.'
        ),
        'target_tooltip': (
            'Loudness objetivo (LUFS) para el botón "Normalizar".\n'
            'Elige el valor según el destino: -23 (TV UE), -24 (TV EEUU), -27 (Netflix),\n'
            '-14/-16 (streaming).'
        ),
    },

    'en': {
        'window_title': 'AudioLoudnessToolkit — 5.1 / Stereo / Mono',
        'mode_label': 'Mode:',
        'mode_51': '5.1 (6 files)',
        'mode_stereo': 'Stereo',
        'mode_mono': 'Mono',
        'tp_label': 'True peak:',
        'tp_precise': 'Precise (4x oversampling)',
        'tp_fast': 'Fast (sample peak)',
        'lang_label': 'Language:',
        'legend_ok': 'has headroom',
        'legend_warn': 'near digital ceiling (normal)',
        'legend_danger': 'clipping risk',

        'ch_front_left': 'Front Left',
        'ch_front_right': 'Front Right',
        'ch_center': 'Center',
        'ch_lfe': 'Subwoofer',
        'ch_surround_left': 'Surround Left',
        'ch_surround_right': 'Surround Right',
        'ch_left': 'Left',
        'ch_right': 'Right',
        'ch_mono': 'Mono',

        'load_file': 'Load file',
        'peak_value': 'Peak: {v:.1f} dBFS',
        'peak_empty': 'Peak: —',
        'rms_value': 'RMS: {v:.1f} dBFS',
        'rms_empty': 'RMS: —',
        'tp_value': 'True Peak: {v:.1f} dBTP',
        'tp_empty': 'True Peak: —',
        'reset': 'Reset',
        'play': '▶ Play',
        'play_stop': '■ Stop',
        'play_tooltip_unavailable': 'sounddevice not available',
        'rate_duration': '{rate} Hz · {dur:.1f} s',

        'stage_loading': 'Loading file...',
        'stage_true_peak': 'Computing true peak...',
        'stage_loudness': 'Computing loudness...',
        'stage_done': 'Done',
        'stage_recompute_tp': 'Recomputing true peak...',
        'analyzing': 'Analyzing...',
        'error_prefix': 'Error: {msg}',

        'loudness_box': 'Integrated loudness (full BS.1770-4 gating)',
        'lufs_empty': '— LUFS',
        'lufs_value': '{v:.1f} LUFS',
        'lu_vs_target': '{v:+.1f} LU vs target',
        'target_label': 'Target (LUFS):',
        'normalize_main': 'Normalize main channels',
        'normalize': 'Normalize',
        'lfe_comp_label': 'LFE compensation:',
        'lfe_minus10': 'LFE −10 dB (remove room gain)',
        'lfe_reset': 'Reset LFE',
        'normalize_limited': (
            'Adjustment limited to {delta:+.1f} dB to avoid exceeding -1 dBTP. '
            'Resulting loudness: {result:.1f} LUFS (target was {target:.1f}).'
        ),

        'summary_box': 'Gain summary',
        'col_channel': 'Channel',
        'col_gain': 'Gain',
        'col_peak_final': 'Final peak',
        'col_tp_final': 'Final TP',
        'gain_value': '{v:+.1f} dB',
        'dash': '—',

        'ffmpeg_box': 'Equivalent ffmpeg filter',
        'copy': 'Copy',

        'export_box': 'Export',
        'format_label': 'Format:',
        'export_mode_label': 'Mode:',
        'export_combined': 'Interleaved (single file)',
        'export_separate': 'Separate (one file per channel)',
        'basename_label': 'Base name:',
        'export_button': 'Export...',
        'export_need_channel': 'Load at least one channel before exporting.',
        'exporting': 'Exporting...',
        'exporting_progress': 'Preparing... ({label}, {idx}/{total})',
        'exporting_encode': 'Encoding to {fmt}... {pct}%',
        'exported': 'Exported: {files}',
        'export_error': 'Export error: {msg}',

        'fmt_wav': 'WAV (24-bit PCM)',
        'fmt_flac': 'FLAC',
        'fmt_aac': 'AAC (.m4a)',
        'fmt_ac3': 'AC3 — Dolby Digital (.mp4)',
        'fmt_eac3': 'E-AC3 — Dolby Digital Plus (.mp4)',
        'fmt_mp3': 'MP3 (stereo downmix if 5.1)',

        'dialog_error': 'Error',
        'dialog_load_audio': 'Load audio',
        'dialog_out_dir': 'Destination folder',

        'standards_btn': 'ⓘ Standards',
        'standards_title': 'Loudness and true peak standards by destination',
        'standards_col_dest': 'Destination',
        'standards_col_lufs': 'Target LUFS',
        'standards_col_tp': 'Max. True Peak',
        'standards_col_norm': 'Standard / reference',
        'close': 'Close',
        'lufs_tooltip': (
            'Integrated loudness of the whole program (full BS.1770-4 gating).\n'
            'Common references: -23 LUFS (EU TV, EBU R128), -24 LUFS (US TV, ATSC A/85),\n'
            '-27 LUFS (Netflix), -14 to -16 LUFS (streaming/music).\n'
            'Click "Standards" for the full table.'
        ),
        'target_tooltip': (
            'Target loudness (LUFS) for the "Normalize" button.\n'
            'Pick the value for your destination: -23 (EU TV), -24 (US TV), -27 (Netflix),\n'
            '-14/-16 (streaming).'
        ),
    },
}


# Tabla de referencia: (destino, LUFS objetivo, True Peak máximo, norma/referencia)
STANDARDS_TABLE = {
    'es': [
        ('TV Europa (broadcast)', '-23 LUFS', '-1 dBTP', 'EBU R128'),
        ('TV EEUU (broadcast)', '-24 LKFS', '-2 dBTP', 'ATSC A/85'),
        ('Netflix 5.1 / Atmos (diálogo)', '-27 LKFS', '-2 dBTP (Atmos: -4 dBTP)', 'Netflix Sound Mix Specs'),
        ('Netflix estéreo', '-27 LUFS', '-2 dBTP', 'Netflix Sound Mix Specs'),
        ('YouTube / streaming general', '-14 LUFS', '-1 dBTP', 'normalización de plataforma'),
        ('Spotify / Apple Music', '-14 a -16 LUFS', '-1 dBTP', 'normalización de plataforma'),
        ('DCP / Cine', 'sin estándar LUFS\n(calibración SPL en sala: 85 dB, fader "7")', 'headroom técnico\nhasta 0 dBFS', 'SMPTE / ISO sala'),
        ('Blu-ray / Home video', '-24 a -27 LUFS\n(práctica habitual)', '-2 a -1 dBTP', 'práctica de industria'),
    ],
    'en': [
        ('EU TV (broadcast)', '-23 LUFS', '-1 dBTP', 'EBU R128'),
        ('US TV (broadcast)', '-24 LKFS', '-2 dBTP', 'ATSC A/85'),
        ('Netflix 5.1 / Atmos (dialogue)', '-27 LKFS', '-2 dBTP (Atmos: -4 dBTP)', 'Netflix Sound Mix Specs'),
        ('Netflix stereo', '-27 LUFS', '-2 dBTP', 'Netflix Sound Mix Specs'),
        ('YouTube / general streaming', '-14 LUFS', '-1 dBTP', 'platform normalization'),
        ('Spotify / Apple Music', '-14 to -16 LUFS', '-1 dBTP', 'platform normalization'),
        ('DCP / Cinema', 'no LUFS standard\n(room SPL calibration: 85 dB, fader "7")', 'technical headroom\nup to 0 dBFS', 'SMPTE / ISO room'),
        ('Blu-ray / Home video', '-24 to -27 LUFS\n(common practice)', '-2 to -1 dBTP', 'industry practice'),
    ],
}


class I18N:
    def __init__(self, lang='es'):
        self.lang = lang

    def set_lang(self, lang):
        if lang in STRINGS:
            self.lang = lang

    def tr(self, key, **kwargs):
        table = STRINGS.get(self.lang, STRINGS['es'])
        text = table.get(key, STRINGS['es'].get(key, key))
        if not kwargs:
            return text
        try:
            return text.format(**kwargs)
        except (ValueError, TypeError):
            return text


i18n = I18N()
