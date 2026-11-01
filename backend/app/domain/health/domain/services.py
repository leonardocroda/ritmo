"""Serviços puros do domínio Health — sem I/O, sem dependências externas."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.domain.health.domain.entities import SleepNight, HRVReading, RHRReading, StressReading, DailyLoad
from app.domain.health.domain.value_objects import (
    HRVStatus, SleepScore, StressLevel, HRVBaseline,
    DoseResponse, DoseResponseBucket, StrengthLifestyle, YogaLifestyle, Lifestyle
)


# Constantes do domínio
HRV_BASELINE_WINDOW_DAYS = 60
HRV_BASELINE_MIN_READINGS = 14
SLEEP_FLOOR_H = 7.0
SLEEP_REM_BAND = (15.0, 25.0)
SLEEP_DEEP_BAND = (15.0, 25.0)


@dataclass(frozen=True, slots=True)
class HRVSignal:
    """Sinal HRV do último dia com dado."""

    value: float
    status: Optional[str]
    date: date


@dataclass(frozen=True, slots=True)
class SleepSignal:
    """Sinal de sono da última noite."""

    duration_s: float
    delta_s: Optional[float]  # vs média 7 noites anteriores
    date: date


@dataclass(frozen=True, slots=True)
class FitnessSignal:
    """Sinal de forma (PMC)."""

    tsb: Optional[float]
    acwr: Optional[float]
    date: date


class HRVCalculator:
    """Calculadora pura de métricas HRV."""

    def compute_baseline(self, readings: Sequence[HRVReading]) -> list[HRVBaseline]:
        """Computa linha de base HRV com média móvel 7d e banda."""
        if len(readings) < HRV_BASELINE_MIN_READINGS:
            return []

        # Ordena por data
        sorted_readings = sorted(readings, key=lambda r: r.date)
        results = []

        for i, reading in enumerate(sorted_readings):
            # Janela de 7 dias até esta leitura
            window_start = reading.date
            window_readings = [
                r for r in sorted_readings[:i+1]
                if (reading.date - r.date).days <= 7
            ]

            if len(window_readings) < 2:
                results.append(HRVBaseline(
                    date=reading.date,
                    value=reading.value,
                    avg7=None,
                    band_low=None,
                    band_high=None,
                ))
                continue

            values = [r.value for r in window_readings]
            avg7 = sum(values) / len(values)
            std = (sum((v - avg7) ** 2 for v in values) / len(values)) ** 0.5
            band_low = avg7 - std
            band_high = avg7 + std

            results.append(HRVBaseline(
                date=reading.date,
                value=reading.value,
                avg7=avg7,
                band_low=band_low,
                band_high=band_high,
            ))

        return results

    def get_current_signal(self, baseline: list[HRVBaseline]) -> Optional[HRVSignal]:
        """Obtém sinal atual a partir da baseline."""
        if not baseline:
            return None
        latest = baseline[-1]
        if latest.avg7 is None:
            return None
        status = None
        if latest.band_low is not None and latest.band_high is not None:
            if latest.value < latest.band_low:
                status = "unbalanced"
            elif latest.value > latest.band_high:
                status = "unbalanced"
            else:
                status = "balanced"
        return HRVSignal(
            value=latest.value,
            status=status,
            date=latest.date,
        )


class SleepCalculator:
    """Calculadora pura de métricas de sono."""

    def compute_regularity(self, nights: Sequence[SleepNight]) -> tuple[float, float] | tuple[None, None]:
        """Média de horários de dormir/acordar em minutos do dia local (±12h trick)."""
        if not nights:
            return (None, None)

        bed_times = []
        wake_times = []

        for night in nights:
            if night.bed_time and night.wake_time:
                bed_min = night.bed_time.hour * 60 + night.bed_time.minute
                wake_min = night.wake_time.hour * 60 + night.wake_time.minute
                # ±12h trick
                if bed_min > 720:  # depois do meio-dia
                    bed_min -= 1440
                bed_times.append(bed_min)
                wake_times.append(wake_min)

        if not bed_times:
            return (None, None)

        avg_bed = sum(bed_times) / len(bed_times)
        avg_wake = sum(wake_times) / len(wake_times)

        # Normaliza de volta para 0-1440
        if avg_bed < 0:
            avg_bed += 1440

        return (avg_bed, avg_wake)

    def weekday_pattern(self, nights: Sequence[SleepNight]) -> list[dict]:
        """Padrão por dia da semana (0=seg, 6=dom)."""
        pattern = {i: {"total_duration": 0.0, "count": 0} for i in range(7)}

        for night in nights:
            wd = night.date.weekday()
            pattern[wd]["total_duration"] += night.duration_s
            pattern[wd]["count"] += 1

        result = []
        for wd in range(7):
            data = pattern[wd]
            avg = data["total_duration"] / data["count"] if data["count"] > 0 else None
            result.append({
                "weekday": wd,
                "avg_duration_s": avg,
                "nights": data["count"],
            })

        return result


class DoseResponseCalculator:
    """Calculadora pura dose-resposta (sono vs HRV/Score)."""

    def compute(
        self,
        nights: Sequence[SleepNight],
        hrv_readings: Sequence[HRVReading],
    ) -> DoseResponse:
        """Computa dose-resposta: curto (<7h), adequado (7-9h), neutro."""
        # Agrupa noites por duração
        short_nights = []
        adequate_nights = []

        for night in nights:
            dur_h = night.duration_s / 3600
            if dur_h < SLEEP_FLOOR_H:
                short_nights.append(night)
            elif dur_h <= 9.0:
                adequate_nights.append(night)

        # Match HRV para noites curtas
        hrv_by_date = {r.date: r.value for r in hrv_readings}
        score_by_date = {n.date: n.score for n in nights if n.score is not None}

        short_hrv = [hrv_by_date[n.date] for n in short_nights if n.date in hrv_by_date]
        short_scores = [score_by_date[n.date] for n in short_nights if n.date in score_by_date]

        adequate_hrv = [hrv_by_date[n.date] for n in adequate_nights if n.date in hrv_by_date]
        adequate_scores = [score_by_date[n.date] for n in adequate_nights if n.date in score_by_date]

        return DoseResponse(
            short=DoseResponseBucket(
                nights=len(short_nights),
                avg_hrv=sum(short_hrv) / len(short_hrv) if short_hrv else None,
                avg_score=sum(short_scores) / len(short_scores) if short_scores else None,
            ),
            adequate=DoseResponseBucket(
                nights=len(adequate_nights),
                avg_hrv=sum(adequate_hrv) / len(adequate_hrv) if adequate_hrv else None,
                avg_score=sum(adequate_scores) / len(adequate_scores) if adequate_scores else None,
            ),
            neutral_nights=len(nights) - len(short_nights) - len(adequate_nights),
        )


class LifestyleCalculator:
    """Calculadora pura de estilo de vida (força + yoga)."""

    def compute(
        self,
        activities: Sequence,  # Atividades genéricas
        activity_types: Sequence[str],  # Tipos de atividade
    ) -> Lifestyle:
        # Placeholder - implementação completa depende dos dados reais
        return Lifestyle(
            strength=StrengthLifestyle(
                streak_weeks=0,
                weeks_hit=0,
                weeks_total=0,
                current_week_sessions=0,
            ),
            yoga=YogaLifestyle(
                sessions=0,
                per_week_avg=0.0,
            ),
        )


class PMCService:
    """Serviço de PMC (CTL/ATL/TSB/ACWR) - delega para training_load domain."""
    pass  # Implementado em training_load domain