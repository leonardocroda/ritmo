"""Equações clássicas de Jack Daniels' Running Formula — funções puras.

Fonte única do cálculo VDOT (design potential-panel): o script de
calibração (`calibrate_vdot.py`) e o painel Potencial importam daqui.
Movidas de `calibrate_vdot.py` sem alteração de assinatura — as mesmas
que geraram a calibração vigente (10K 41:15 -> 50.2).
"""

import math


def vo2_cost(speed_m_per_min: float) -> float:
    """Custo de oxigênio para uma dada velocidade (m/min)."""
    return -4.60 + 0.182258 * speed_m_per_min + 0.000104 * speed_m_per_min ** 2


def fraction_vo2max(time_min: float) -> float:
    """Fração do VO2max sustentável por um dado tempo (minutos)."""
    return (
        0.8
        + 0.1894393 * math.exp(-0.012778 * time_min)
        + 0.2989558 * math.exp(-0.1932605 * time_min)
    )


def calculate_vdot(distance_m: float, total_seconds: float) -> float:
    """Calcula VDOT a partir de distância (m) e tempo total (s)."""
    time_min = total_seconds / 60.0
    speed_m_per_min = distance_m / time_min
    return vo2_cost(speed_m_per_min) / fraction_vo2max(time_min)


def speed_for_vo2(vo2: float) -> float:
    """Inverte a equação de custo de corrida; retorna velocidade em m/min."""
    discriminant = 0.182258 ** 2 + 4 * 0.000104 * (vo2 + 4.60)
    if discriminant < 0:
        raise ValueError("Não foi possível calcular a velocidade para este VDOT.")
    return (-0.182258 + math.sqrt(discriminant)) / (2 * 0.000104)


def pace_for_fraction(vdot: float, fraction: float) -> float:
    """Ritmo em s/km para uma fração do VDOT."""
    speed_m_per_min = speed_for_vo2(vdot * fraction)
    return 60_000.0 / speed_m_per_min


def equivalent_time(vdot: float, distance_km: float) -> float:
    """Resolve o tempo (s) cuja equação de Daniels resulta no VDOT informado."""
    lo, hi = 1.0, 100_000.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if calculate_vdot(distance_km * 1000, mid) > vdot:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2
