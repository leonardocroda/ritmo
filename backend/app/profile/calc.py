"""Matemática das zonas de FC (feature hr-zones) — funções puras (AD-003).

Sem DB, sem I/O — a mesma entrada devolve sempre os mesmos valores,
pinável em teste (padrão do health/calc.py). Entradas: método
(lthr | fcr | fcmax), bounds = lista de 5 dicts ``{"low", "high"}`` em
pontos percentuais (o wrapper ``{"zones": [...]}`` é só o formato de
armazenamento) e métricas em bpm. Saída: zonas em bpm ``{"n", "low",
"high"}`` — Z5 do lthr é aberta (high None); fcr/fcmax fecham em 100%
(= fcmax). Semântica de zona: ``low ≤ FC < high`` (spec HRZ-10).
Arredondamento: ``round`` do Python, bpm inteiro (decisão do spec).
"""

# Defaults por método (HRZ-08): lthr 65/80/89/95/100 — tabela do
# usuário, Z5 aberta; fcr e fcmax 50/60/70/80/90 — Karvonen/Polar-ACSM,
# Z5 fecha em 100%.
DEFAULT_BOUNDS: dict[str, list[dict]] = {
    "lthr": [
        {"low": 65, "high": 80},
        {"low": 80, "high": 89},
        {"low": 89, "high": 95},
        {"low": 95, "high": 100},
        {"low": 100, "high": None},
    ],
    "fcr": [
        {"low": 50, "high": 60},
        {"low": 60, "high": 70},
        {"low": 70, "high": 80},
        {"low": 80, "high": 90},
        {"low": 90, "high": 100},
    ],
    "fcmax": [
        {"low": 50, "high": 60},
        {"low": 60, "high": 70},
        {"low": 70, "high": 80},
        {"low": 80, "high": 90},
        {"low": 90, "high": 100},
    ],
}

# Zonas esperadas — validação estrutural dos bounds (HRZ-09)
ZONE_COUNT = 5


class BoundsError(Exception):
    """HRZ-09 → 422: bounds inválidos — o motivo aponta o primeiro
    ponto inválido (índice da zona), mensagem PT-BR."""


def validate_bounds(method: str, bounds: list[dict]) -> None:
    """Guardrails dos percentuais (HRZ-09), primeiro ponto no motivo.

    Rejeita: ≠5 zonas, ``z1.low ≤ 0``, cadeia não ascendente (cada
    ``z[n].high == z[n+1].low`` e crescente dentro da zona), zona <1
    ponto percentual e high indevido na Z5 — None no lthr (zona
    aberta), 100 no fcr/fcmax (fecha em fcmax)."""
    if len(bounds) != ZONE_COUNT:
        raise BoundsError(f"esperadas 5 zonas, recebidas {len(bounds)}")
    if bounds[0]["low"] <= 0:
        raise BoundsError("zona 1: low deve ser maior que zero")
    for i in range(ZONE_COUNT - 1):
        zone = bounds[i]
        if zone["high"] is None or zone["high"] - zone["low"] < 1:
            raise BoundsError(
                f"zona {i + 1}: high deve ser no mínimo 1 ponto acima de low"
            )
        if bounds[i + 1]["low"] != zone["high"]:
            raise BoundsError(
                f"zona {i + 2}: low deve ser igual ao high da zona {i + 1}"
            )
    z5 = bounds[ZONE_COUNT - 1]
    if method == "lthr":
        if z5["high"] is not None:
            raise BoundsError("zona 5: high deve ser null no método lthr (zona aberta)")
    else:
        if z5["high"] != 100:
            raise BoundsError(f"zona 5: high deve ser 100 no método {method}")
        if z5["high"] - z5["low"] < 1:
            raise BoundsError("zona 5: high deve ser no mínimo 1 ponto acima de low")


def zones_bpm(
    method: str, bounds: list[dict], metrics: dict[str, int | None]
) -> list[dict] | None:
    """Deriva as zonas em bpm (HRZ-10) — None quando a métrica exigida
    pelo método não existe (HRZ-11, estado vazio honesto).

    lthr: ``round(pct × fclthr / 100)``; fcr (Karvonen):
    ``fcrest + round(pct × (fcmax − fcrest) / 100)``; fcmax:
    ``round(pct × fcmax / 100)``. Z5: lthr high None (aberta);
    fcr/fcmax high = fcmax (fecha em 100%)."""
    if method == "lthr":
        fclthr = metrics.get("fclthr")
        if fclthr is None:
            return None
        return [
            {
                "n": i + 1,
                "low": round(z["low"] * fclthr / 100),
                "high": round(z["high"] * fclthr / 100) if z["high"] is not None else None,
            }
            for i, z in enumerate(bounds)
        ]
    if method == "fcr":
        fcrest = metrics.get("fcrest")
        fcmax = metrics.get("fcmax")
        if fcrest is None or fcmax is None:
            return None
        zones = [
            {
                "n": i + 1,
                "low": fcrest + round(z["low"] * (fcmax - fcrest) / 100),
                "high": fcrest + round(z["high"] * (fcmax - fcrest) / 100),
            }
            for i, z in enumerate(bounds)
        ]
        zones[ZONE_COUNT - 1]["high"] = fcmax
        return zones
    if method == "fcmax":
        fcmax = metrics.get("fcmax")
        if fcmax is None:
            return None
        zones = [
            {
                "n": i + 1,
                "low": round(z["low"] * fcmax / 100),
                "high": round(z["high"] * fcmax / 100),
            }
            for i, z in enumerate(bounds)
        ]
        zones[ZONE_COUNT - 1]["high"] = fcmax
        return zones
    raise ValueError(f"método desconhecido: {method}")


def classify(hr: int, zones: list[dict]) -> int | None:
    """Número da zona de uma FC (HRZ-10): ``low ≤ FC < high``; Z5 aberta
    (high None: qualquer FC ≥ low); None fora (guard — abaixo da Z1,
    não ocorre com Z5 aberta)."""
    for zone in zones:
        if zone["high"] is None:
            if hr >= zone["low"]:
                return zone["n"]
        elif zone["low"] <= hr < zone["high"]:
            return zone["n"]
    return None
