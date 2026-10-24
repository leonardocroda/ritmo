"""Captura os prints do site com a API MOCKADA (dados ilustrativos exemplares).

O problema que resolve: os prints do site precisam ser bonitos e a
interface é 100% real — então a saída honesta é mockar os DADOS, não a
tela. Este script sobe o Chromium contra o frontend de verdade (build
standalone) e intercepta TODAS as chamadas `/api/*` pelo Playwright
(`page.route`), entregando payloads exemplares e coerentes entre si —
mesma postura do doc de identidade v0.3: "dados ilustrativos — nenhum
dado real de usuário".

A persona dos dados: corredor de 28 anos treinando para a Meia Best
Açaí (08/11/2026, alvo ~1:27), VDOT corrente 52,0 (10K 40:12) com
demonstrado 54,6 (5K 18:35), sono em ordem, HRV estável na faixa e a
semana equilibrada — o veredito "Pronto pra qualidade".

Uso:
    RITMO_BASE=http://localhost:3100 python scripts/site/capture_mock.py

Requisitos: build standalone de pé (`npm run build` + os passos de
copia do static/public — ver README) e `playwright` Python instalado.
"""

import json
import math
import sys
import urllib.parse
from datetime import date, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:3100"
OUT = Path(__file__).resolve().parents[2] / "public" / "prints"
VIEWPORT = {"width": 390, "height": 844}
SCALE = 2

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def say(msg: str) -> None:
    print(msg, flush=True)


# ------------------------------------------------------------------ #
# Utilidades de dados                                                  #
# ------------------------------------------------------------------ #

TODAY = date(2026, 10, 24)  # sábado — o "hoje" da persona


def iso(d: date) -> str:
    return d.strftime("%Y-%m-%d")


def days_back(n: int) -> list[date]:
    """n datas terminando hoje (inclusive)."""
    return [TODAY - timedelta(days=n - 1 - i) for i in range(n)]


def jitter(i: int, k: int = 0, m: int = 100) -> float:
    """Pseudo-ruído determinístico em [0, 1) — nada de random module."""
    v = ((i * 37 + k * 17 + 11) % m) / m
    return v


# ------------------------------------------------------------------ #
# Home (`/api/home/today`)                                             #
# ------------------------------------------------------------------ #

def home_today() -> dict:
    strip = [(TODAY - timedelta(days=6 - i)) for i in range(7)]
    loads = [165, 0, 72, 118, 152, 0, 0]
    return {
        "date": iso(TODAY),
        "verdict": {
            "phrase": "Pronto pra qualidade",
            "tone": "good",
            "rule": "HRV na faixa, sono acima da média e forma positiva",
        },
        "signals": {
            "hrv": {"value": 74, "status": "BALANCED", "as_of": iso(TODAY)},
            "sleep": {"duration_s": 27720, "delta_s": 1920, "as_of": iso(TODAY)},
            "fitness": {"tsb": 5.2, "acwr": 1.0, "as_of": iso(TODAY)},
        },
        "strip": [
            {"date": iso(d), "load": load} for d, load in zip(strip, loads)
        ],
        "last_activity": {
            "id": 231,
            "date": "2026-10-22",
            "distance_m": 14600,
            "evaluated": True,
        },
        "volume": {"week_km": 44.2, "avg4_km": 40.8, "delta_pct": 8.3},
        "countdown": {"name": "Meia Best Açaí", "date": "2026-11-08", "days_left": 15},
        "recommendations": [
            {
                "text": "Boa janela pra 2×3km no limiar",
                "support": "HRV dentro da faixa pela primeira manhã em 3 dias e sono acima da média. O plano pede qualidade — a janela está aberta.",
                "why": "HRV · sono · forma",
                "tone": "good",
            },
            {
                "text": "Café depois das 16h custou ~32min de sono",
                "support": None,
                "why": "N = 11 noites",
                "tone": "attention",
            },
        ],
        "volume_weeks": [
            {"week_start": "2026-08-17", "km": 33.8},
            {"week_start": "2026-08-24", "km": 36.2},
            {"week_start": "2026-08-31", "km": 38.5},
            {"week_start": "2026-09-07", "km": 35.9},
            {"week_start": "2026-09-14", "km": 39.8},
            {"week_start": "2026-09-21", "km": 41.2},
            {"week_start": "2026-09-28", "km": 43.5},
            {"week_start": "2026-10-05", "km": 40.9},
            {"week_start": "2026-10-12", "km": 42.7},
            {"week_start": "2026-10-19", "km": 44.2},
        ],
        "predictions": [
            {"event": "10K", "time_s": 2384},
            {"event": "HALF_MARATHON", "time_s": 5225},
        ],
    }


# ------------------------------------------------------------------ #
# Treinos: lista + detalhe do 2×3km (`/api/activities*`)                #
# ------------------------------------------------------------------ #

def activities_list() -> dict:
    items = [
        (231, "2026-10-22T06:12:00", "2×3km no limiar", 14600, 4139, 283, 148, "limiar", True),
        (229, "2026-10-20T06:31:00", "Fácil pelo parque", 10200, 3246, 318, 141, "facil", False),
        (226, "2026-10-18T06:58:00", "Longão 20,1km", 20100, 5388, 268, 149, "longao", True),
        (224, "2026-10-17T06:40:00", "Regenerativo", 6400, 2132, 333, 132, "facil", False),
        (221, "2026-10-15T06:05:00", "Progressivo 12km", 12000, 3400, 283, 145, "progressivo", True),
        (219, "2026-10-13T06:22:00", "Fácil matinal", 8000, 2490, 311, 138, "facil", False),
        (217, "2026-10-12T07:10:00", "Prova 10K — 40:12", 10000, 2412, 241, 168, "prova", False),
        (215, "2026-10-11T06:15:00", "Tempo run 14,8km", 14800, 4180, 282, 152, "tempo", False),
    ]
    return {
        "items": [
            {
                "id": i,
                "start_time": start,
                "activity_type": "running",
                "name": name,
                "distance_m": dist,
                "duration_s": dur,
                "pace_s": pace,
                "avg_hr": hr,
                "inferred_type": kind,
                "evaluated": evaluated,
            }
            for (i, start, name, dist, dur, pace, hr, kind, evaluated) in items
        ],
        "total": 8,
        "limit": 30,
        "offset": 0,
    }


def zone_meta() -> list[dict]:
    """Zonas VDOT 52 — cores são as do backend (fonte única)."""
    return [
        {"key": "easy", "label": "Easy", "pace_range": "5:31/km-4:45/km", "color": "#22c55e"},
        {"key": "marathon", "label": "Maratona", "pace_range": "4:22/km", "color": "#3b82f6"},
        {"key": "threshold", "label": "Limiar", "pace_range": "4:06/km-4:18/km", "color": "#f97316"},
        {"key": "interval", "label": "Intervalado", "pace_range": "3:52/km-3:42/km", "color": "#ef4444"},
        {"key": "repetition", "label": "Repetição", "pace_range": "3:32/km", "color": "#a855f7"},
    ]


def featured_detail() -> dict:
    """O treino do print: 2×3km no limiar — voltas com largura
    proporcional (aquecimento/tiro/rec/desaquecimento) e avaliação no
    alvo."""
    laps = [
        # (dist_m, pace_s, hr, cad, temp, elev, zone)
        (3200, 312, 133, 172, 21.0, 12, "easy"),
        (3000, 248, 164, 182, 20.5, 8, "threshold"),
        (1200, 304, 146, 174, 20.0, 4, "easy"),
        (3000, 246, 166, 182, 20.0, 6, "threshold"),
        (4200, 308, 138, 170, 19.5, 10, "easy"),
    ]
    splits, cumulative = [], 0.0
    for idx, (dist, pace, hr, cad, temp, elev, zone) in enumerate(laps, start=1):
        duration = round(dist / 1000 * pace)
        cumulative += dist
        splits.append(
            {
                "idx": idx,
                "dist_m": dist,
                "duration_s": duration,
                "pace_s": pace,
                "avg_hr": hr,
                "avg_cadence": cad,
                "avg_temperature": temp,
                "elevation_m": elev,
                "intensity_type": "active",
                "zone": zone,
                "km_label": f"{cumulative / 1000:.1f}".replace(".", ","),
            }
        )
    return {
        "activity": {
            "id": 231,
            "start_time": "2026-10-22T06:12:00",
            "activity_type": "running",
            "name": "2×3km no limiar",
            "distance_m": 14600,
            "duration_s": 4139,
            "pace_s": 283,
            "avg_hr": 148,
            "max_hr": 172,
            "avg_cadence": 177,
            "elevation_gain_m": 40,
            "aerobic_te": 3.4,
            "anaerobic_te": 0.8,
            "training_load": 152,
            "evaluated": True,
            "inferred_type": "limiar",
            "structure": "aquecimento 3,2km · 2×3km no limiar (rec 1,2km) · desaquecimento 4,2km",
        },
        "splits": splits,
        "zones": zone_meta(),
        "hr_color": "#f8fafc",
        "consistency": {
            "first_half_pace_s": 284,
            "second_half_pace_s": 282,
            "balance_delta_s": -2,
            "balance_delta_pct": -0.7,
            "first_half_hr": 146,
            "second_half_hr": 148,
            "hr_drift_bpm": 2,
            "decoupling_pct": 0.8,
            "cadence_fade_spm": -1,
        },
        "context": {
            "sleep": {"duration_s": 25380, "score": 80},
            "hrv": {"value": 72, "status": "BALANCED"},
            "rhr": {"value": 44},
            "temperature_c": 20.3,
        },
        "evaluations": [
            {
                "id": 12,
                "activity_id": 231,
                "intent_type": "limiar",
                "intent_text": "2×3km a 4:05–4:10, rec de 1,2km",
                "verdict": "on_target",
                "verdict_json": {
                    "veredito": "on_target",
                    "headline": "Dois tiros firmes no limiar — execução limpa",
                    "execucao_vs_intencao": {
                        "pct_zona_alvo": 91.7,
                        "principais_desvios": [
                            "Primeiros 400m do primeiro tiro 6s acima da faixa (ansiedade de largada)"
                        ],
                    },
                    "o_que_funcionou": [
                        "Recuperação rolando a 5:04 sem oscilar entre os tiros",
                        "FC estável entre tiros (164 → 166 bpm) e segundo tiro mais rápido",
                    ],
                    "corrigir_prox_vez": [
                        "Fechar o aquecimento com 2 strides leves — o primeiro tiro demora a encontrar o ritmo"
                    ],
                    "contexto_relevante": [
                        "ACWR 1,0 — semana equilibrada antes da qualidade",
                        "Noite de 7h05 antes do treino e HRV 72 na faixa",
                    ],
                    "confianca": "alta",
                },
                "model": "z-ai/glm-5.3",
                "prompt_version": "v3",
                "tokens_in": 3184,
                "tokens_out": 1628,
                "status": "done",
                "error": None,
                "created_at": "2026-10-22T20:41:12",
            }
        ],
    }


# ------------------------------------------------------------------ #
# Performance (`/api/potential`)                                       #
# ------------------------------------------------------------------ #

def potential() -> dict:
    return {
        "vdot": {
            "current": {"vdot": 52.0, "source": "10K em 40:12", "test_date": "2026-10-12"},
            "demonstrated": {"vdot": 54.6, "source": "5K", "date": "2026-08-30"},
            "gap_pct": 95.2,
            "timeline": [
                {"date": "2026-03-22", "vdot": 49.8, "source": "10K", "label": "10K 42:36", "distance_m": 10000, "time_s": 2556},
                {"date": "2026-05-09", "vdot": 51.3, "source": "Meia", "label": "Meia 1:31:02", "distance_m": 21097, "time_s": 5462},
                {"date": "2026-06-20", "vdot": 52.4, "source": "5K", "label": "5K 19:07", "distance_m": 5000, "time_s": 1147},
                {"date": "2026-08-30", "vdot": 54.6, "source": "5K", "label": "5K 18:35", "distance_m": 5000, "time_s": 1115},
                {"date": "2026-10-12", "vdot": 52.0, "source": "10K", "label": "10K 40:12", "distance_m": 10000, "time_s": 2412},
            ],
        },
        "predictions": {
            "5K": {"garmin_s": 1122, "riegel_s": 1115, "vdot_s": 1121, "average_s": 1119, "pr_s": 1115, "pr_date": "2026-08-30"},
            "10K": {"garmin_s": 2418, "riegel_s": 2324, "vdot_s": 2410, "average_s": 2384, "pr_s": 2412, "pr_date": "2026-10-12"},
            "HALF_MARATHON": {"garmin_s": 5280, "riegel_s": 5130, "vdot_s": 5265, "average_s": 5225, "pr_s": 5462, "pr_date": "2026-05-09"},
            "MARATHON": {"garmin_s": 11124, "riegel_s": 10693, "vdot_s": 11150, "average_s": 10989, "pr_s": None, "pr_date": None},
        },
        "vo2max": {
            "points": [
                {"date": "2026-08-07", "value": 51.0},
                {"date": "2026-08-14", "value": 51.1},
                {"date": "2026-08-21", "value": 51.3},
                {"date": "2026-08-28", "value": 51.2},
                {"date": "2026-09-04", "value": 51.6},
                {"date": "2026-09-11", "value": 51.8},
                {"date": "2026-09-18", "value": 52.0},
                {"date": "2026-09-25", "value": 52.3},
                {"date": "2026-10-02", "value": 52.2},
                {"date": "2026-10-09", "value": 52.6},
                {"date": "2026-10-16", "value": 52.9},
                {"date": "2026-10-23", "value": 53.2},
            ]
        },
        "decay": [
            {"event": "5K", "real_pace_s": 223, "ideal_pace_s": 224, "delta_pct": -0.4},
            {"event": "10K", "real_pace_s": 241.2, "ideal_pace_s": 239, "delta_pct": 0.9},
            {"event": "HALF_MARATHON", "real_pace_s": 258.9, "ideal_pace_s": 253.5, "delta_pct": 2.1},
        ],
        "pmc": pmc_block(),
    }


def pmc_block() -> dict:
    """Curva de 60d com final saudável: fitness subindo, forma +5,2 e
    ACWR 1,0 — coerente com os sinais da Home."""
    dates = days_back(60)
    points = []
    for i, d in enumerate(dates):
        t = i / 59
        ctl = 124.0 + 17.2 * t + (jitter(i, 1) - 0.5) * 2.2
        atl = 118.0 + 18.0 * t + 7.5 * math.sin(i / 4.7) + (jitter(i, 2) - 0.5) * 3
        tsb = ctl - atl
        acwr = min(1.15, max(0.78, 0.95 + 0.12 * math.sin(i / 9) + (jitter(i, 3) - 0.5) * 0.06))
        points.append(
            {
                "date": iso(d),
                "ctl": round(ctl, 1),
                "atl": round(atl, 1),
                "tsb": round(tsb, 1),
                "acwr": round(acwr, 2),
            }
        )
    # Final exato — os destaques do dia batem com a Home (forma +5,2).
    points[-1] = {"date": iso(TODAY), "ctl": 141.2, "atl": 136.0, "tsb": 5.2, "acwr": 1.0}
    return {"days": 60, "points": points, "current": points[-1]}


# ------------------------------------------------------------------ #
# Saúde (`/api/health/summary`)                                        #
# ------------------------------------------------------------------ #

def health_summary() -> dict:
    dates = days_back(60)
    short_nights = {"2026-09-05", "2026-09-26", "2026-10-17"}  # < 6h
    friday_hole = {"2026-09-11", "2026-10-02", "2026-10-23"}  # sexta curta
    sleep_points, hrv_points = [], []
    hrv_values = []
    for i, d in enumerate(dates):
        d_iso = iso(d)
        # sexta é o buraco (o padrão da persona) + 3 noites ruins
        if d_iso in short_nights:
            duration = 21000 + int(jitter(i, 4) * 1200)  # ~5h50
            score, rem = 66, 19
            hrv_val = 61 + int(jitter(i, 5) * 3)
        elif d_iso in friday_hole:
            duration = 22900 + int(jitter(i, 6) * 900)  # ~6h22
            score, rem = 73, 21
            hrv_val = 67 + int(jitter(i, 7) * 3)
        else:
            duration = 25800 + int(jitter(i, 8) * 3600)  # 7h10–8h10
            score, rem = 80 + int(jitter(i, 9) * 11), 23 + int(jitter(i, 10) * 6)
            hrv_val = 70 + int(jitter(i, 11) * 8)
        hrv_values.append(hrv_val)
        bed_h, bed_m = 22, 40 + int(jitter(i, 12) * 40)
        wake_h, wake_m = 6, 5 + int(jitter(i, 13) * 30)
        sleep_points.append(
            {
                "date": d_iso,
                "duration_s": duration,
                "score": score,
                "rem_pct": rem,
                "deep_pct": 13 + int(jitter(i, 14) * 5),
                "light_pct": 52 + int(jitter(i, 15) * 6),
                "awakenings": int(jitter(i, 16) * 4),
                "bed_local": f"{bed_h:02d}:{bed_m:02d}",
                "wake_local": f"{wake_h:02d}:{wake_m:02d}",
            }
        )
        # média móvel 7d + banda (a partir de 14 valores na janela)
        window = hrv_values[-7:]
        avg7 = round(sum(window) / len(window), 1) if len(window) == 7 else None
        band = (i >= 13, None, None)
        hrv_points.append(
            {
                "date": d_iso,
                "value": hrv_val,
                "avg7": avg7,
                "band_low": round(avg7 - 6.4, 1) if i >= 13 else None,
                "band_high": round(avg7 + 6.4, 1) if i >= 13 else None,
            }
        )
    hrv_points[-1]["value"] = 74  # o chip da Home: HRV 74ms na faixa
    below_floor = sum(1 for p in sleep_points if p["duration_s"] < 25200)
    return {
        "sleep": {
            "days": 60,
            "floor_s": 25200,
            "rem_band": [21, 31],
            "below_floor": {"nights": below_floor, "pct": round(below_floor / 60 * 100)},
            "regularity": {"avg_bed_min": 1384, "avg_wake_min": 382},
            "weekday_pattern": [
                {"weekday": 0, "avg_duration_s": 26280, "nights": 9},
                {"weekday": 1, "avg_duration_s": 26100, "nights": 9},
                {"weekday": 2, "avg_duration_s": 25980, "nights": 8},
                {"weekday": 3, "avg_duration_s": 25620, "nights": 9},
                {"weekday": 4, "avg_duration_s": 22920, "nights": 8},
                {"weekday": 5, "avg_duration_s": 27900, "nights": 8},
                {"weekday": 6, "avg_duration_s": 28440, "nights": 9},
            ],
            "points": sleep_points,
        },
        "hrv": {
            "points": hrv_points,
            "current": {
                "date": iso(TODAY),
                "value": 74,
                "avg7": 72.4,
                "band_low": 66.0,
                "band_high": 78.8,
                "status": "BALANCED",
            },
        },
        "rhr": {
            "points": [
                {
                    "date": iso(d),
                    "value": round(44 - 0.02 * i + (jitter(i, 17) - 0.5) * 1.8),
                }
                for i, d in enumerate(dates)
            ],
            "baseline": 44,
        },
        "stress": {
            "points": [
                {
                    "date": iso(d),
                    "avg": round(28 + 6 * math.sin(i / 5) + (jitter(i, 18) - 0.5) * 8),
                }
                for i, d in enumerate(dates)
            ],
            "avg_window": 29,
        },
        "dose_response": {
            "short": {"nights": 3, "avg_hrv": 64, "avg_score": 72},
            "adequate": {"nights": 46, "avg_hrv": 74, "avg_score": 84},
            "neutral_nights": 11,
        },
        "lifestyle": {
            "strength": {
                "streak_weeks": 4,
                "weeks_hit": 8,
                "weeks_total": 9,
                "current_week_sessions": 2,
            },
            "yoga": {"sessions": 24, "per_week_avg": 2.9},
        },
    }


# ------------------------------------------------------------------ #
# Perfil: zonas de FC + conexão                                        #
# ------------------------------------------------------------------ #

def hr_zones() -> dict:
    lthr_bounds = [
        {"low": 65, "high": 80},
        {"low": 80, "high": 89},
        {"low": 89, "high": 95},
        {"low": 95, "high": 100},
        {"low": 100, "high": None},
    ]
    return {
        "metrics": {
            "fcmax": {"value": 199, "source": "garmin", "valid_from": "2026-10-20"},
            "fcrest": {"value": 42, "source": "garmin", "valid_from": "2026-10-24"},
            "fclthr": {"value": 183, "source": "garmin", "valid_from": "2026-10-21"},
        },
        "modes": {"fcmax": "garmin", "fcrest": "garmin", "fclthr": "garmin"},
        "config": {
            "method": "lthr",
            "bounds": {"zones": lthr_bounds},
            "valid_from": "2026-10-21",
        },
        "zones": [
            {"n": 1, "low": 119, "high": 146},
            {"n": 2, "low": 146, "high": 163},
            {"n": 3, "low": 163, "high": 174},
            {"n": 4, "low": 174, "high": 183},
            {"n": 5, "low": 183, "high": None},
        ],
        "defaults": {
            "lthr": lthr_bounds,
            "fcr": [
                {"low": 50, "high": 60},
                {"low": 60, "high": 70},
                {"low": 70, "high": 80},
                {"low": 80, "high": 90},
                {"low": 90, "high": None},
            ],
            "fcmax": [
                {"low": 50, "high": 60},
                {"low": 60, "high": 70},
                {"low": 70, "high": 80},
                {"low": 80, "high": 90},
                {"low": 90, "high": 100},
            ],
        },
    }


def hr_zones_history() -> dict:
    return {
        "metrics": [
            {"kind": "fcmax", "value": 199, "source": "garmin", "valid_from": "2026-10-20"},
            {"kind": "fclthr", "value": 183, "source": "garmin", "valid_from": "2026-10-21"},
            {"kind": "fcrest", "value": 42, "source": "garmin", "valid_from": "2026-10-24"},
            {"kind": "fcmax", "value": 197, "source": "garmin", "valid_from": "2026-09-13"},
            {"kind": "fcrest", "value": 44, "source": "garmin", "valid_from": "2026-09-24"},
        ],
        "configs": [
            {
                "method": "lthr",
                "bounds": {
                    "zones": [
                        {"low": 65, "high": 80},
                        {"low": 80, "high": 89},
                        {"low": 89, "high": 95},
                        {"low": 95, "high": 100},
                        {"low": 100, "high": None},
                    ]
                },
                "valid_from": "2026-10-21",
            },
            {
                "method": "fcr",
                "bounds": {
                    "zones": [
                        {"low": 50, "high": 60},
                        {"low": 60, "high": 70},
                        {"low": 70, "high": 80},
                        {"low": 80, "high": 90},
                        {"low": 90, "high": None},
                    ]
                },
                "valid_from": "2026-09-05",
            },
        ],
    }


# ------------------------------------------------------------------ #
# Despacho das rotas                                                   #
# ------------------------------------------------------------------ #

def make_api_handler() -> "callable":
    detail = featured_detail()

    def handler(route, request):
        parsed = urllib.parse.urlsplit(request.url)
        path = parsed.path
        if path == "/api/auth/me":
            payload = {"id": 1, "email": "leonardo@ritmo.run", "display_name": "Leonardo"}
        elif path == "/api/sync/jobs/latest":
            payload = {
                "job": {
                    "id": 42,
                    "status": "done",
                    "started_at": "2026-10-24T06:11:04",
                    "finished_at": "2026-10-24T06:11:52",
                    "error": None,
                    "stats": {
                        "step": "done",
                        "message": "Sync concluído",
                        "activities_new": 0,
                        "activities_updated": 2,
                        "splits": 9,
                        "sleep_days": 3,
                        "hrv_days": 3,
                        "rhr_days": 3,
                        "battery_days": 3,
                        "stress_days": 3,
                        "records": 0,
                        "calls_made": 23,
                        "duration_s": 48,
                        "warnings": [],
                        "reauth_needed": False,
                    },
                }
            }
        elif path == "/api/home/today":
            payload = home_today()
        elif path == "/api/activities":
            payload = activities_list()
        elif path.startswith("/api/activities/"):
            payload = detail
        elif path == "/api/potential":
            payload = potential()
        elif path == "/api/health/summary":
            payload = health_summary()
        elif path == "/api/profile/hr-zones":
            payload = hr_zones()
        elif path == "/api/profile/hr-zones/history":
            payload = hr_zones_history()
        elif path == "/api/profile/garmin-connection":
            payload = {"state": "connected", "tokens_updated_at": "2026-10-24T06:11:52"}
        else:
            say(f"  (rota de API não mockada: {path})")
            payload = {}
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(payload),
        )

    return handler


# ------------------------------------------------------------------ #
# Capturas                                                             #
# ------------------------------------------------------------------ #

def shoot(page, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(OUT / name))
    say(f"  ok {name}")


def shoot_element(page, selector: str, name: str) -> None:
    el = page.locator(selector).first
    el.scroll_into_view_if_needed()
    page.wait_for_timeout(400)
    OUT.mkdir(parents=True, exist_ok=True)
    el.screenshot(path=str(OUT / name))
    say(f"  ok {name}")


def settle(page, selector: str, ms: int = 2200) -> None:
    page.wait_for_selector(selector, state="visible", timeout=30_000)
    page.wait_for_timeout(ms)
    page.evaluate("document.fonts.ready")


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--hide-scrollbars"])
        context = browser.new_context(viewport=VIEWPORT, device_scale_factor=SCALE)
        # Sessão falsa: o proxy é otimista (checa presença do cookie) e a
        # API real nunca é chamada — tudo /api/* cai no mock.
        context.add_cookies(
            [{"name": "ritmo_session", "value": "mock", "url": BASE}]
        )
        context.route("**/api/**", make_api_handler())
        page = context.new_page()

        def go(path: str) -> None:
            page.goto(f"{BASE}{path}", wait_until="load")

        # ---- Home (raiz) ----
        say("home (raiz)")
        go("/")
        settle(page, 'h2:text-is("Pronto pra qualidade")')
        shoot(page, "hoje-top.png")
        page.get_by_text("Volume · últimas 10 semanas").scroll_into_view_if_needed()
        page.evaluate("window.scrollBy(0, -300)")
        page.wait_for_timeout(1200)
        shoot(page, "hoje-abaixo.png")

        # ---- Treinos: lista + detalhe do 2×3km ----
        say("treinos — lista")
        go("/treinos")
        settle(page, 'a[href^="/treinos/"]')
        shoot(page, "treinos-list.png")

        say("treinos — detalhe (id 231)")
        go("/treinos/231")
        settle(page, "h1")
        shoot(page, "treino-detail.png")
        shoot_element(page, 'section:has(h2:text-is("Contexto do dia"))', "contexto-dia.png")
        shoot_element(page, 'section:has(h2:text-is("Voltas")) div.rounded-card', "splits-chart.png")
        shoot_element(page, 'section:has(h2:text-is("Avaliação")) div.rounded-card', "evaluation-card.png")

        # ---- Performance ----
        say("performance")
        go("/performance")
        settle(page, 'h2:text-is("Onde estou")')
        shoot(page, "performance-top.png")
        shoot_element(page, 'section:has(h2:text-is("Onde estou")) div.mt-3', "performance-vdot.png")
        shoot_element(page, 'section:has(h2:text-is("O que isso prevê")) div.mt-3', "predictions.png")
        shoot_element(page, 'section:has(h2:text-is("Carga de treino")) div.rounded-card', "pmc-chart.png")

        # ---- Saúde ----
        say("saúde")
        go("/saude")
        settle(page, 'h2:text-is("Sono")')
        shoot(page, "saude-top.png")
        shoot_element(page, 'section:has(h2:text-is("Sono")) div.rounded-card >> nth=0', "sleep-chart.png")
        shoot_element(page, 'section:has(h2:text-is("Recuperação")) div.rounded-card >> nth=0', "hrv-chart.png")
        shoot_element(page, 'section:has(h2:text-is("Dose-resposta")) div.mt-3', "dose-response.png")

        # ---- Perfil (zonas de FC) ----
        say("perfil")
        go("/perfil")
        settle(page, 'h2:text-is("Conexão Garmin")', ms=1200)
        shoot(page, "perfil-top.png")
        shoot_element(page, 'section:has(h2:text-is("Valores")) div.mt-3', "hr-values.png")
        shoot_element(page, 'section:has(h2:text-is("Método e zonas")) div.mt-3', "hr-zones.png")

        browser.close()
        say(f"prints ilustrativos em {OUT}")


if __name__ == "__main__":
    main()
