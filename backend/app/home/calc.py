"""Motor do painel Home — veredito, recomendações e leituras puras (design).

Sem DB, sem I/O, zero LLM (AD-003 + decisão do spec: o veredito diário
é regra pura) — a mesma entrada devolve sempre o mesmo resultado. Os
sinais entram como dataclasses tipadas montadas pelo service; sinal
ausente é None e NUNCA sustenta regra (neutro). Sem NENHUM sinal
(banco vazio de saúde/carga) o veredito é None — o estado vazio que
orienta o primeiro sync, distinto de V6 ("dia comum" = existe dado,
nenhuma regra dispara).

O piso de sono é o MESMO do painel Saúde (import direto — nunca duas
réguas para a mesma pergunta); health/calc é stdlib puro, então este
módulo continua sem DB/IO.
"""

from dataclasses import dataclass
from datetime import date

from app.health.calc import SLEEP_FLOOR_S

# Thresholds do veredito (spec §Assumptions): janela de qualidade
# TSB > 0 · fadiga TSB < −10 · carga alta ACWR > 1,5 · taper ≤ 14 dias
# da prova (TAPER_DAYS sustenta as recomendações R1–R5).
TSB_QUALITY = 0
TSB_FATIGUE = -10
ACWR_HIGH = 1.5
TAPER_DAYS = 14


@dataclass(frozen=True)
class HrvSignal:
    """HRV do último dia com dado (bloco `current` do Saúde, AD-010):
    status BALANCED | UNBALANCED | None ("coletando linha de base")."""

    value: float
    status: str | None
    as_of: date


@dataclass(frozen=True)
class SleepSignal:
    """Última noite dormida — duração em segundos."""

    duration_s: float
    as_of: date


@dataclass(frozen=True)
class FitnessSignal:
    """Forma: última linha da PMC — TSB (frescor) e ACWR (carga)."""

    tsb: float | None
    acwr: float | None
    as_of: date


@dataclass(frozen=True)
class Signals:
    """Os 3 sinais que sustentam o veredito; cada um None = sem dado."""

    hrv: HrvSignal | None = None
    sleep: SleepSignal | None = None
    fitness: FitnessSignal | None = None


@dataclass(frozen=True)
class Verdict:
    """Uma frase por dia: a frase, o tom semântico e a regra que a emitiu."""

    phrase: str
    tone: str
    rule: str


def verdict(signals: Signals) -> Verdict | None:
    """Cadeia de prioridade fixa V1→V6 — o primeiro casamento vence
    (HOME-09): uma frase por dia, nunca duas. Sinal ausente é neutro:
    nunca sustenta regra de bom nem de ruim (HOME-10). Sem NENHUM
    sinal -> None (estado vazio — o payload deriva sem campo extra).
    """
    hrv, sleep, fitness = signals.hrv, signals.sleep, signals.fitness
    if hrv is None and sleep is None and fitness is None:
        return None

    below_floor = sleep is not None and sleep.duration_s < SLEEP_FLOOR_S
    unbalanced = hrv is not None and hrv.status == "UNBALANCED"
    balanced = hrv is not None and hrv.status == "BALANCED"
    high_load = (
        fitness is not None and fitness.acwr is not None and fitness.acwr > ACWR_HIGH
    )
    fatigued = (
        fitness is not None and fitness.tsb is not None and fitness.tsb < TSB_FATIGUE
    )
    fresh = fitness is not None and fitness.tsb is not None and fitness.tsb > TSB_QUALITY

    if unbalanced and below_floor:
        return Verdict("Recuperação em dívida", "alert", "V1")
    if unbalanced:
        return Verdict("Corpo pedindo leve", "attention", "V2")
    if high_load:
        return Verdict("Carga alta — segure o volume", "attention", "V3")
    if fatigued:
        return Verdict("Acúmulo de fadiga", "attention", "V4")
    if balanced and fresh and not below_floor:
        return Verdict("Pronto pra qualidade", "good", "V5")
    return Verdict("Dia comum, sem urgências", "neutral", "V6")


@dataclass(frozen=True)
class Recommendation:
    """Ação do dia: o texto, a linha de apoio (só onde o spec define
    copy), a tag why (sinais que sustentam) e o tom semântico."""

    text: str
    support: str | None
    why: str | None
    tone: str


def recommendations(rule: str | None, countdown_days: int | None) -> list[Recommendation]:
    """R1–R5 por prioridade fixa, cap 3 (HOME-25..30).

    R1–R3 e R5 casam 1:1 com a regra do veredito (uma frase por dia ->
    no máximo uma dessas por payload); R4 (taper) dispara
    INDEPENDENTE do veredito quando faltam ≤14 dias para a próxima
    prova. `why` é a tag dos sinais que sustentam a recomendação (None
    em R5: nenhuma regra específica — o 'Tudo dentro da faixa' vive no
    support). Sem veredito (estado vazio) não há recomendação: nada
    para basear uma ação.
    """
    recs: list[Recommendation] = []
    if rule == "V5":
        recs.append(
            Recommendation(
                "Boa janela pra sessão de qualidade", None, "HRV · sono · forma", "good"
            )
        )
    elif rule in ("V1", "V2"):
        recs.append(
            Recommendation(
                "Priorize recuperação hoje — leve ou descanso",
                None,
                "HRV · sono",
                "alert" if rule == "V1" else "attention",
            )
        )
    elif rule in ("V3", "V4"):
        recs.append(
            Recommendation(
                "Segure o volume nesta semana", None, "ACWR · forma", "attention"
            )
        )
    if countdown_days is not None and countdown_days <= TAPER_DAYS:
        recs.append(
            Recommendation(
                "Semana de prova — redução progressiva (taper)",
                None,
                f"prova em {countdown_days} dias",
                "attention",
            )
        )
    if rule == "V6":
        recs.append(
            Recommendation(
                "Siga o leve de hoje", "Tudo dentro da faixa", None, "neutral"
            )
        )
    return recs[:3]
