"""
loudness.py — Implementación BS.1770-4 con gateo, optimizada para feedback interactivo.

Estrategia:
  1. Filtrado K-weighting (una vez por canal, O(N), via scipy.signal.lfilter).
  2. Cálculo de z[i,j] (media de cuadrados por bloque de 400ms, 75% overlap)
     mediante suma acumulada -> O(N), una sola vez por canal.
  3. Gateo + integración: O(numBlocks) (~tamaño bloques de 0.1s), recalculable
     instantáneamente cada vez que cambia la ganancia de un canal.

Los pasos 1-2 son el "Analizar" (coste único, ~segundos para un largometraje).
El paso 3 se recalcula en cada cambio de fader -> respuesta instantánea.
"""

import numpy as np
from scipy.signal import lfilter

# Coeficientes K-weighting (RBJ cookbook, IEC/ITU-R BS.1770-4), dependientes de fs.
def _high_shelf_coeffs(rate, G=4.0, Q=1/np.sqrt(2), fc=1500.0):
    A = 10 ** (G / 40.0)
    w0 = 2.0 * np.pi * (fc / rate)
    alpha = np.sin(w0) / (2.0 * Q)
    b0 = A * ((A + 1) + (A - 1) * np.cos(w0) + 2 * np.sqrt(A) * alpha)
    b1 = -2 * A * ((A - 1) + (A + 1) * np.cos(w0))
    b2 = A * ((A + 1) + (A - 1) * np.cos(w0) - 2 * np.sqrt(A) * alpha)
    a0 = (A + 1) - (A - 1) * np.cos(w0) + 2 * np.sqrt(A) * alpha
    a1 = 2 * ((A - 1) - (A + 1) * np.cos(w0))
    a2 = (A + 1) - (A - 1) * np.cos(w0) - 2 * np.sqrt(A) * alpha
    return np.array([b0, b1, b2]) / a0, np.array([a0, a1, a2]) / a0


def _high_pass_coeffs(rate, G=0.0, Q=0.5, fc=38.0):
    w0 = 2.0 * np.pi * (fc / rate)
    alpha = np.sin(w0) / (2.0 * Q)
    b0 = (1 + np.cos(w0)) / 2
    b1 = -(1 + np.cos(w0))
    b2 = (1 + np.cos(w0)) / 2
    a0 = 1 + alpha
    a1 = -2 * np.cos(w0)
    a2 = 1 - alpha
    return np.array([b0, b1, b2]) / a0, np.array([a0, a1, a2]) / a0


def k_weight(data, rate):
    """Aplica el filtro K-weighting completo (high-shelf + high-pass) a una señal mono."""
    b1, a1 = _high_shelf_coeffs(rate)
    b2, a2 = _high_pass_coeffs(rate)
    stage1 = lfilter(b1, a1, data)
    stage2 = lfilter(b2, a2, stage1)
    return stage2


def block_meansquares(filtered, rate, block_size=0.4, overlap=0.75):
    """
    Media de cuadrados por bloque de gateo (vectorizado via suma acumulada).
    Devuelve un array z de longitud numBlocks, igual definición que BS.1770-4 eq.1.
    """
    n = filtered.shape[0]
    step = 1.0 - overlap
    window = int(block_size * rate)
    hop = block_size * step * rate

    t = n / rate
    num_blocks = int(np.round((t - block_size) / (block_size * step))) + 1
    if num_blocks < 1:
        num_blocks = 1

    sq = filtered.astype(np.float64) ** 2
    cumsq = np.concatenate([[0.0], np.cumsum(sq)])

    j = np.arange(num_blocks)
    l = (j * hop).astype(np.int64)
    u = (j * hop + window).astype(np.int64)
    l = np.clip(l, 0, n)
    u = np.clip(u, 0, n)

    z = (cumsq[u] - cumsq[l]) / window
    return z


def gated_loudness(z_list, gains_db, G):
    """
    Integra loudness con gateo BS.1770-4 a partir de z[i] cacheados (gain=0)
    y una ganancia en dB por canal. O(numBlocks), instantáneo.

    z_list   : lista de arrays z (uno por canal, mismo numBlocks)
    gains_db : lista de ganancias en dB por canal (misma longitud que z_list)
    G        : lista de pesos de canal BS.1770 (1.0 / 1.41 / 0 para LFE)
    """
    num_channels = len(z_list)
    factors = [10 ** (g / 10.0) for g in gains_db]  # ganancia en potencia
    z = np.stack([z_list[i] * factors[i] for i in range(num_channels)], axis=0)

    Gamma_a = -70.0
    with np.errstate(divide='ignore'):
        loud_per_block = -0.691 + 10.0 * np.log10(
            sum(G[i] * z[i] for i in range(num_channels))
        )

    abs_gated = loud_per_block >= Gamma_a
    if not np.any(abs_gated):
        return float('-inf')

    z_avg_abs = np.array([np.mean(z[i][abs_gated]) for i in range(num_channels)])
    with np.errstate(divide='ignore'):
        gamma_r = -0.691 + 10.0 * np.log10(
            sum(G[i] * z_avg_abs[i] for i in range(num_channels))
        ) - 10.0

    rel_gated = abs_gated & (loud_per_block > gamma_r)
    if not np.any(rel_gated):
        return float('-inf')

    z_avg_rel = np.array([np.mean(z[i][rel_gated]) for i in range(num_channels)])
    with np.errstate(divide='ignore'):
        lufs = -0.691 + 10.0 * np.log10(
            sum(G[i] * z_avg_rel[i] for i in range(num_channels))
        )
    return float(lufs)


# Pesos de canal BS.1770-4 por configuración (orden SMPTE/ffmpeg)
CHANNEL_WEIGHTS = {
    1: {'M': 1.0},
    2: {'L': 1.0, 'R': 1.0},
    6: {'L': 1.0, 'R': 1.0, 'C': 1.0, 'LFE': 0.0, 'Ls': 1.41, 'Rs': 1.41},
}
