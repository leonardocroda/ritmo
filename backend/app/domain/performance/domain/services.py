"""Serviços puros do domínio Performance — VDOT, Daniels, Predições."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.domain.activities.domain.entities import Activity
from app.domain.performance.domain.entities import (
    VDOTProfile, TimelinePoint, Prediction, DecayPoint, VO2maxPoint
)
from app.domain.performance.domain.value_objects import VDOT, EventDistance, RaceTime


# Tabela Daniels VDOT (simplificada - usar tabela completa em produção)
DANIELS_VDOT_TABLE = {
    # (distancia_m, tempo_s): vdot
    (5000, 1800): 55.0,  # 5K 30:00
    (5000, 1500): 65.0,  # 5K 25:00
    (10000, 3600): 55.0, # 10K 60:00
    (10000, 3000): 65.0, # 10K 50:00
    (21097, 7200): 55.0, # Meia 2h
    (42195, 14400): 55.0, # Maratona 4h
}


@dataclass(frozen=True, slots=True)
class VDOTCalculation:
    """Resultado do cálculo VDOT."""

    vdot: float
    source: str
    test_date: date
    distance_m: float
    time_s: float


class VDOTCalculator:
    """Calculadora VDOT baseada em Jack Daniels."""

    def calculate_from_activity(self, activity: Activity) -> Optional[VDOTCalculation]:
        """Calcula VDOT a partir de uma atividade (se for corrida válida)."""
        if not activity.is_running or activity.distance_m < 3000:
            return None

        # Usa tabela Daniels ou fórmula aproximada
        vdot = self._estimate_vdot(activity.distance_m, activity.duration_s)

        return VDOTCalculation(
            vdot=vdot,
            source="activity",
            test_date=activity.start_time.date(),
            distance_m=activity.distance_m,
            time_s=activity.duration_s,
        )

    def calculate_from_race(self, distance_m: float, time_s: float, race_date: date) -> VDOTCalculation:
        """Calcula VDOT a partir de tempo de prova oficial."""
        vdot = self._estimate_vdot(distance_m, time_s)
        return VDOTCalculation(
            vdot=vdot,
            source="race",
            test_date=race_date,
            distance_m=distance_m,
            time_s=time_s,
        )

    def _estimate_vdot(self, distance_m: float, time_s: float) -> float:
        """Estima VDOT usando fórmula aproximada."""
        # Fórmula simplificada: VDOT ≈ (distância_km / tempo_min) * 100 * fator
        pace_min_per_km = (time_s / 60) / (distance_m / 1000)
        speed_kmh = 60 / pace_min_per_km
        # Aproximação grosseira
        return max(30.0, min(85.0, speed_kmh * 1.5))


class PredictionService:
    """Serviço de predições de prova."""

    def predict_all(self, vdot: float) -> dict[str, dict]:
        """Prediz tempos para eventos padrão."""
        results = {}
        for event in EventDistance.standard_events():
            ideal_time = self._predict_vdot(vdot, event.meters)
            results[event.key] = {
                "vdot_s": ideal_time,
                "event": event.label,
            }
        return results

    def _predict_vdot(self, vdot: float, distance_m: float) -> float:
        """Prediz tempo baseado no VDOT."""
        # Fórmula simplificada
        pace = 100 / vdot * 60  # min/km aprox
        return pace * (distance_m / 1000) * 60


class DecayCalculator:
    """Calculadora de decay (desempenho real vs ideal)."""

    def compute_decay(self, activities: Sequence[Activity], vdot: float) -> list:
        """Computa decay para eventos onde há dados reais."""
        decay_points = []
        for event in EventDistance.standard_events():
            # Busca melhor tempo real para esta distância
            real_activities = [
                a for a in activities
                if a.is_running and abs(a.distance_m - event.meters) < event.meters * 0.1
            ]
            if not real_activities:
                continue

            best = min(real_activities, key=lambda a: a.duration_s)
            real_pace = best.duration_s / (best.distance_m / 1000)
            ideal_pace = self._ideal_pace(vdot, event.meters)

            delta_pct = ((real_pace - ideal_pace) / ideal_pace) * 100

            decay_points.append({
                "event": event.key,
                "real_pace_s": real_pace,
                "ideal_pace_s": ideal_pace,
                "delta_pct": round(delta_pct, 1),
            })

        return decay_points

    def _ideal_pace(self, vdot: float, distance_m: float) -> float:
        # Placeholder
        return 300.0  # 5:00/km


class VO2maxService:
    """Serviço de timeline VO2max."""

    def build_timeline(self, activities: Sequence[Activity]) -> list:
        """Constrói timeline de VO2max a partir de atividades."""
        points = []
        for a in activities:
            if a.is_running and a.distance_m >= 3000:
                # Estima VO2max da atividade
                vo2max = self._estimate_vo2max(a)
                points.append(VO2maxPoint(
                    date=a.start_time.date(),
                    value=vo2max,
                ))
        return sorted(points, key=lambda p: p.date)

    def _estimate_vo2max(self, activity: Activity) -> float:
        # Placeholder - Garmin já provê isso
        return 55.0