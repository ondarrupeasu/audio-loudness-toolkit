import numpy as np
import pyloudnorm as pyln
import sys
sys.path.insert(0, '.')
from core.loudness import k_weight, block_meansquares, gated_loudness, CHANNEL_WEIGHTS

RATE = 48000
DUR = 6.0  # segundos, suficiente para varios bloques de gateo


def make_test_signal(rate, dur, freq, amp, seed):
    rng = np.random.default_rng(seed)
    n = int(rate * dur)
    t = np.arange(n) / rate
    tone = amp * np.sin(2 * np.pi * freq * t)
    # añadimos un tramo de silencio al principio para forzar el gateo relativo
    silence_n = int(rate * 1.5)
    tone[:silence_n] = 0.0
    return tone.astype(np.float64)


def test_stereo_matches_pyloudnorm():
    L = make_test_signal(RATE, DUR, 1000, 0.1, 1)
    R = make_test_signal(RATE, DUR, 1000, 0.1, 2)
    data = np.stack([L, R], axis=1)

    meter = pyln.Meter(RATE)
    ref = meter.integrated_loudness(data)

    z_L = block_meansquares(k_weight(L, RATE), RATE)
    z_R = block_meansquares(k_weight(R, RATE), RATE)
    G = [CHANNEL_WEIGHTS[2]['L'], CHANNEL_WEIGHTS[2]['R']]
    ours = gated_loudness([z_L, z_R], [0.0, 0.0], G)

    print(f"Estéreo  pyloudnorm={ref:.4f}  nuestro={ours:.4f}  diff={abs(ref-ours):.6f}")
    assert abs(ref - ours) < 0.01


def test_51_drops_lfe_and_weights_surrounds():
    labels = ['L', 'R', 'C', 'LFE', 'Ls', 'Rs']
    chans = {lab: make_test_signal(RATE, DUR, 1000 + i * 37, 0.08, i + 10)
             for i, lab in enumerate(labels)}
    # LFE con mucha energía de baja frecuencia: si NO se excluye, distorsionaría el resultado
    chans['LFE'] = make_test_signal(RATE, DUR, 50, 0.5, 99)

    # referencia pyloudnorm: solo soporta 5 canales, orden L R C Ls Rs (sin LFE)
    data5 = np.stack([chans['L'], chans['R'], chans['C'], chans['Ls'], chans['Rs']], axis=1)
    meter = pyln.Meter(RATE)
    ref = meter.integrated_loudness(data5)

    z = {lab: block_meansquares(k_weight(chans[lab], RATE), RATE) for lab in labels}
    G = [CHANNEL_WEIGHTS[6][lab] for lab in labels]
    ours = gated_loudness([z[lab] for lab in labels], [0.0] * 6, G)

    print(f"5.1      pyloudnorm(sin LFE)={ref:.4f}  nuestro(con LFE, peso 0)={ours:.4f}  diff={abs(ref-ours):.6f}")
    assert abs(ref - ours) < 0.01


def test_gain_adjustment_matches_recompute():
    """La versión rápida con ganancia debe coincidir con recalcular desde cero con la señal escalada."""
    L = make_test_signal(RATE, DUR, 1000, 0.05, 5)
    R = make_test_signal(RATE, DUR, 1200, 0.05, 6)
    G = [CHANNEL_WEIGHTS[2]['L'], CHANNEL_WEIGHTS[2]['R']]

    gain_db_L = 4.0
    gain_db_R = -2.0
    factor_L = 10 ** (gain_db_L / 20.0)
    factor_R = 10 ** (gain_db_R / 20.0)

    # camino rápido: z cacheado a gain=0 + ganancia aplicada algebraicamente
    z_L = block_meansquares(k_weight(L, RATE), RATE)
    z_R = block_meansquares(k_weight(R, RATE), RATE)
    fast = gated_loudness([z_L, z_R], [gain_db_L, gain_db_R], G)

    # camino lento: recalcular todo sobre la señal ya escalada
    z_L2 = block_meansquares(k_weight(L * factor_L, RATE), RATE)
    z_R2 = block_meansquares(k_weight(R * factor_R, RATE), RATE)
    slow = gated_loudness([z_L2, z_R2], [0.0, 0.0], G)

    print(f"Ganancia rápido={fast:.4f}  recálculo completo={slow:.4f}  diff={abs(fast-slow):.6f}")
    assert abs(fast - slow) < 0.01


if __name__ == '__main__':
    test_stereo_matches_pyloudnorm()
    test_51_drops_lfe_and_weights_surrounds()
    test_gain_adjustment_matches_recompute()
    print("OK - todos los tests pasan")
