# Verificador de audio — 5.1 / Estéreo / Mono

App de escritorio (Python + PySide6) para analizar y preparar audio
multicanal: peak, RMS, true peak (preciso o rápido), loudness integrado
con gateo BS.1770-4 completo (equivalente a Fairlight), ajuste de
ganancia por canal con feedback instantáneo, reproducción con barra de
posición (seek), y exportación combinada o por canal en
WAV / FLAC / AAC / AC3 / E-AC3 / MP3. Interfaz en español e inglés
(selector arriba a la derecha). Barra de progreso durante análisis,
recálculo de true peak y exportación.

Si `sounddevice` da problemas al instalar (depende de PortAudio), la app
funciona igual — solo se desactiva el reproductor (▶ Reproducir).

## Probar en tu Mac

```bash
cd verificador_audio
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

Si `sounddevice` da problemas al instalar (depende de PortAudio), la app
funciona igual — solo se desactiva el reproductor.

## Tests (sin interfaz, verifican el núcleo)

```bash
python3 test_loudness.py   # valida el gateo BS.1770 contra pyloudnorm
python3 test_io.py         # decodificación/codificación multi-formato, true peak
python3 test_analysis.py   # flujo completo con un caso sintético tipo "película"
QT_QPA_PLATFORM=offscreen python3 test_ui.py        # interfaz sin pantalla
QT_QPA_PLATFORM=offscreen python3 test_load_routing.py  # enrutamiento de carga por canal
QT_QPA_PLATFORM=offscreen python3 test_features.py  # i18n, progreso, export en segundo plano, player
```

## Estructura

```
core/
  io.py        — decodificación (cualquier formato vía ffmpeg), exportación, true peak
  loudness.py  — K-weighting + gateo BS.1770-4, validado contra pyloudnorm
  analysis.py  — orquestación: Channel, modos, normalizar, filtro ffmpeg, exportar
ui/
  main_window.py      — ventana principal
  widgets.py          — medidores de barra
  player.py           — reproducción con seek (sounddevice)
  i18n.py             — textos ES/EN
  standards_dialog.py — ventana de referencia (estándares LUFS/True Peak)
  workers.py          — análisis y exportación en segundo plano (no bloquea la UI)
  tp_worker.py        — recálculo de true peak en segundo plano
main.py
AudioLoudnessToolkit.spec — receta de empaquetado para PyInstaller (ver abajo)
```

## Empaquetar como .app

El archivo `AudioLoudnessToolkit.spec` ya incluye las reglas para que PyInstaller
empaquete los binarios de ffmpeg (`imageio-ffmpeg`), libsndfile (`soundfile`)
y PortAudio (`sounddevice`), que normalmente quedan fuera del análisis
automático. Con el venv activado:

```bash
pip install pyinstaller pyinstaller-hooks-contrib
pyinstaller AudioLoudnessToolkit.spec
```

Esto genera `dist/AudioLoudnessToolkit.app` (modo `--onedir`: arranca más rápido
que `--onefile` y es más fácil depurar si algo falla).

La primera vez que lo abras, macOS (Gatekeeper) avisará de que es de un
desarrollador no identificado — clic derecho → Abrir, una sola vez. No
requiere conexión a internet ni instalar nada más.

Para probarlo desde terminal (verás cualquier traceback si falla al arrancar):

```bash
dist/AudioLoudnessToolkit/AudioLoudnessToolkit
```

Si da algún error de import, de ffmpeg no encontrado, o de audio
(`PortAudio library not found`), copia el mensaje completo y lo ajustamos
— normalmente es una línea extra de `datas`/`binaries` en el `.spec`.
