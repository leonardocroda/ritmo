"""Service de séries de FC (feature hr-zones) — resolução e escrita.

Métricas e configs são séries effective-dated append-only (HRZ-12): a
vigente em D é a de maior (valid_from, id) com valid_from ≤ D — duas
mudanças no mesmo dia são legítimas, resolvidas pelo tie-break id
DESC. Escritas são idempotentes (valor igual ao vigente → sem linha
nova, HRZ-03) e o manual-wins vive AQUI (HRZ-06): garmin nunca cria
linha quando a vigente é manual — sync e router herdam a regra.
Validação cross-field (HRZ-04) carrega campo e motivo exatos; o
router só mapeia para 422. Quem chama controla o commit.
"""

from datetime import date

from sqlalchemy.orm import Session

from app.db.models import HrZoneConfig, UserHrMetric
from app.profile.calc import zones_bpm

# As 3 métricas fisiológicas da feature (spec P1)
METRIC_KINDS = ("fcmax", "fcrest", "fclthr")

# Limites de sanidade (HRZ-04): teto Strava no fcmax, réguas fisiológicas
METRIC_LIMITS = {
    "fcmax": (100, 230),
    "fcrest": (30, 110),
    "fclthr": (100, 220),
}


class MetricValidationError(Exception):
    """HRZ-04 → 422: métrica fora dos limites ou incoerente — carrega o
    campo e o motivo exatos (o router aponta o campo na resposta)."""

    def __init__(self, field: str, reason: str) -> None:
        self.field = field
        super().__init__(reason)


def metric_on(db: Session, user_id: int, kind: str, on_date: date) -> UserHrMetric | None:
    """Linha vigente da métrica em on_date (HRZ-12) — maior
    (valid_from, id) com valid_from ≤ on_date; None quando nunca
    configurada."""
    return (
        db.query(UserHrMetric)
        .filter(
            UserHrMetric.user_id == user_id,
            UserHrMetric.kind == kind,
            UserHrMetric.valid_from <= on_date,
        )
        .order_by(UserHrMetric.valid_from.desc(), UserHrMetric.id.desc())
        .first()
    )


def metrics_on(db: Session, user_id: int, on_date: date) -> dict[str, UserHrMetric | None]:
    """As 3 kinds vigentes em on_date — linha ou None por kind (HRZ-01)."""
    return {kind: metric_on(db, user_id, kind, on_date) for kind in METRIC_KINDS}


def config_on(db: Session, user_id: int, on_date: date) -> HrZoneConfig | None:
    """Config de zonas vigente em on_date — mesmo tie-break da métrica."""
    return (
        db.query(HrZoneConfig)
        .filter(
            HrZoneConfig.user_id == user_id,
            HrZoneConfig.valid_from <= on_date,
        )
        .order_by(HrZoneConfig.valid_from.desc(), HrZoneConfig.id.desc())
        .first()
    )


def zones_on(
    db: Session, user_id: int, on_date: date
) -> tuple[HrZoneConfig | None, list[dict] | None]:
    """Config vigente + zonas em bpm derivadas na leitura (HRZ-12/10) —
    (None, None) sem config; (config, None) sem a métrica exigida pelo
    método (HRZ-11: estado vazio honesto, não erro)."""
    config = config_on(db, user_id, on_date)
    if config is None:
        return None, None
    metrics = metrics_on(db, user_id, on_date)
    values = {
        kind: row.value_bpm if row is not None else None
        for kind, row in metrics.items()
    }
    return config, zones_bpm(config.method, config.bounds["zones"], values)


def set_metric(
    db: Session,
    user_id: int,
    kind: str,
    value: int,
    source: str,
    on_date: date | None = None,
) -> bool:
    """Insere mudança de métrica (HRZ-02) — append-only, nunca update.

    False sem linha nova quando: valor igual ao vigente em on_date
    (HRZ-03, idempotente — o check precede o manual-wins) ou a escrita
    é garmin e a vigente é manual (HRZ-06 — manual-wins). True cria a
    linha com valid_from = on_date (default hoje)."""
    on_date = on_date or date.today()
    current = metric_on(db, user_id, kind, on_date)
    if current is not None:
        if current.value_bpm == value:
            return False
        if source == "garmin" and current.source == "manual":
            return False
    db.add(
        UserHrMetric(
            user_id=user_id, kind=kind, value_bpm=value, source=source,
            valid_from=on_date,
        )
    )
    db.flush()  # id disponível para o tie-break; quem chama commita
    return True


def set_config(
    db: Session,
    user_id: int,
    method: str,
    bounds: list[dict],
    on_date: date | None = None,
) -> bool:
    """Insere config nova (HRZ-08/09) — idempotente vs método+bounds
    vigentes (mesma config → False, sem linha). True cria a linha."""
    on_date = on_date or date.today()
    current = config_on(db, user_id, on_date)
    if current is not None and current.method == method and current.bounds == {
        "zones": bounds
    }:
        return False
    db.add(
        HrZoneConfig(
            user_id=user_id, method=method, bounds={"zones": bounds},
            valid_from=on_date,
        )
    )
    db.flush()
    return True


def validate_metrics_set(
    current: dict[str, int | None], updates: dict[str, int | None]
) -> None:
    """Valida o conjunto MERGE (HRZ-04): limites por métrica e
    incoerências cross-field (fcrest ≥ fcmax, fclthr ≥ fcmax) — mesmo
    quando a incoerência só existe entre o vigente e o update."""
    merged = {**current, **updates}
    for kind, (low, high) in METRIC_LIMITS.items():
        value = merged.get(kind)
        if value is not None and not low <= value <= high:
            raise MetricValidationError(kind, f"deve estar entre {low} e {high} bpm")
    fcmax = merged.get("fcmax")
    if fcmax is None:
        return
    fcrest = merged.get("fcrest")
    if fcrest is not None and fcrest >= fcmax:
        raise MetricValidationError("fcrest", "FC de repouso acima da FC máxima")
    fclthr = merged.get("fclthr")
    if fclthr is not None and fclthr >= fcmax:
        raise MetricValidationError("fclthr", "limiar acima da FC máxima")
