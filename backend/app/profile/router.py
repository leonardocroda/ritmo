"""Router do perfil — zonas de FC (feature hr-zones), user-scope.

Padrão do health/potential (modelos de saída inline + require_session):
GET resolve métricas/config/zonas vigentes hoje (+ preferência de posse
por métrica); PUT é a única escrita (valores e/ou método e/ou bounds e/
ou preferências de posse, `source=manual` nas métricas) com resposta no
shape do GET — 422 por campo apontando o motivo (HRZ-04) e 422 com o
primeiro ponto inválido nos bounds (HRZ-09); history lista as séries
DESC por (valid_from, id) com data e fonte (HRZ-15). O commit é único
no fim do PUT: 422 depois de um flush descarta a escrita parcial.
A conexão Garmin (garmin-tokens-db) entra como GET de leitura — só
metadados do estado (GTDB-17), derivação no service.
"""

from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.deps import require_session
from app.db.engine import get_db
from app.db.models import HrZoneConfig, User, UserHrMetric
from app.profile import calc, service

router = APIRouter(prefix="/api/profile")


class MetricOut(BaseModel):
    value: int
    source: str
    valid_from: date


class ConfigOut(BaseModel):
    method: str
    bounds: dict
    valid_from: date


class ZoneOut(BaseModel):
    n: int
    low: int
    high: int | None


class HrZonesOut(BaseModel):
    metrics: dict[str, MetricOut | None]
    modes: dict[str, str]
    config: ConfigOut | None
    zones: list[ZoneOut] | None
    defaults: dict[str, list[dict]]


class ZoneIn(BaseModel):
    """Percentuais por zona — o schema valida TIPOS; contagem, cadeia e
    teto da Z5 são do domínio (validate_bounds), para o 422 apontar o
    primeiro ponto inválido em vez do erro genérico do schema."""

    low: int
    high: int | None


class BoundsIn(BaseModel):
    zones: list[ZoneIn]


class MetricsIn(BaseModel):
    fcmax: int | None = None
    fcrest: int | None = None
    fclthr: int | None = None


class HrZonesUpdate(BaseModel):
    metrics: MetricsIn | None = None
    method: Literal["lthr", "fcr", "fcmax"] | None = None
    bounds: BoundsIn | None = None
    sync_modes: dict[str, Literal["garmin", "manual"]] | None = None


class MetricHistoryOut(BaseModel):
    kind: str
    value: int
    source: str
    valid_from: date


class ConfigHistoryOut(BaseModel):
    method: str
    bounds: dict
    valid_from: date


class HrZonesHistoryOut(BaseModel):
    metrics: list[MetricHistoryOut]
    configs: list[ConfigHistoryOut]


class ConnectionOut(BaseModel):
    """GTDB-17: SÓ metadados da conexão — estado + data da última escrita
    dos tokens; nunca o blob (fica no cofre cifrado do tokens_store)."""

    state: Literal["connected", "reauth_needed", "not_connected"]
    tokens_updated_at: datetime | None


def _hr_zones_payload(db: Session, user_id: int) -> HrZonesOut:
    """Monta o shape completo (GET e resposta do PUT) a partir das
    séries vigentes hoje: métricas {value, source, valid_from}|null por
    kind, preferência de posse por kind (HRZ-22), config|null, zonas
    derivadas|null e defaults dos 3 métodos."""
    today = date.today()
    metrics = service.metrics_on(db, user_id, today)
    config = service.config_on(db, user_id, today)
    zones = None
    if config is not None:
        values = {
            kind: row.value_bpm if row is not None else None
            for kind, row in metrics.items()
        }
        zones = calc.zones_bpm(config.method, config.bounds["zones"], values)
    return HrZonesOut(
        metrics={
            kind: (
                MetricOut(
                    value=row.value_bpm, source=row.source, valid_from=row.valid_from
                )
                if row is not None
                else None
            )
            for kind, row in metrics.items()
        },
        modes={kind: service.sync_mode(db, user_id, kind) for kind in service.METRIC_KINDS},
        config=(
            ConfigOut(
                method=config.method, bounds=config.bounds, valid_from=config.valid_from
            )
            if config is not None
            else None
        ),
        zones=zones,
        defaults=calc.DEFAULT_BOUNDS,
    )


@router.get("/hr-zones")
def get_hr_zones(
    user: User = Depends(require_session),
    db: Session = Depends(get_db),
) -> HrZonesOut:
    """HRZ-01/10/11: valores vigentes, config, zonas derivadas em bpm
    (null sem config ou sem a métrica exigida — estado vazio honesto) e
    defaults para prefill (HRZ-08). Toda leitura é do usuário da sessão."""
    return _hr_zones_payload(db, user.id)


@router.put("/hr-zones")
def put_hr_zones(
    payload: HrZonesUpdate,
    user: User = Depends(require_session),
    db: Session = Depends(get_db),
) -> HrZonesOut:
    """HRZ-02/03/04/08/09 + HRZ-20/21: a única escrita — métricas (merge
    validado, linhas manuais que registram a preferência `manual`),
    método (sem bounds -> defaults do método), bounds custom (método
    herdado da config vigente) e/ou preferências de posse (`sync_modes`:
    "voltar a puxar do Garmin" registra `garmin`; o próximo sync
    reassume). Escrita toda com valid_from = hoje; resposta no shape do
    GET."""
    today = date.today()
    updates: dict[str, int] = {}
    if payload.metrics is not None:
        updates = {
            kind: value
            for kind, value in payload.metrics.model_dump().items()
            if value is not None
        }
    method = payload.method
    bounds = (
        [zone.model_dump() for zone in payload.bounds.zones]
        if payload.bounds is not None
        else None
    )
    sync_modes = payload.sync_modes or None  # {} = nada (422 abaixo)

    if not updates and method is None and bounds is None and sync_modes is None:
        raise HTTPException(status_code=422, detail="nada para atualizar")

    if sync_modes is not None:
        for kind, mode in sync_modes.items():
            if kind not in service.METRIC_KINDS:
                raise HTTPException(
                    status_code=422, detail=f"{kind}: métrica desconhecida"
                )
            service.set_sync_mode(db, user.id, kind, mode)  # HRZ-20/21

    if updates:
        current = service.metrics_on(db, user.id, today)
        current_values = {
            kind: row.value_bpm if row is not None else None
            for kind, row in current.items()
        }
        try:
            service.validate_metrics_set(current_values, updates)
        except service.MetricValidationError as exc:
            raise HTTPException(
                status_code=422, detail=f"{exc.field}: {exc}"
            ) from exc
        for kind, value in updates.items():
            service.set_metric(db, user.id, kind, value, source="manual", on_date=today)

    if method is not None or bounds is not None:
        if method is None:
            config = service.config_on(db, user.id, today)
            if config is None:
                raise HTTPException(
                    status_code=422, detail="bounds exigem um método configurado"
                )
            method = config.method  # edge: muda só o percentual -> método fica
        if bounds is None:
            bounds = calc.DEFAULT_BOUNDS[method]  # HRZ-08: defaults do método
        try:
            calc.validate_bounds(method, bounds)
        except calc.BoundsError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        service.set_config(db, user.id, method, bounds, on_date=today)

    db.commit()
    return _hr_zones_payload(db, user.id)


@router.get("/hr-zones/history")
def get_hr_zones_history(
    user: User = Depends(require_session),
    db: Session = Depends(get_db),
) -> HrZonesHistoryOut:
    """HRZ-15: mudanças de métricas e configs, mais recente primeiro —
    DESC por (valid_from, id), com data e fonte."""
    metric_rows = (
        db.query(UserHrMetric)
        .filter(UserHrMetric.user_id == user.id)
        .order_by(UserHrMetric.valid_from.desc(), UserHrMetric.id.desc())
        .all()
    )
    config_rows = (
        db.query(HrZoneConfig)
        .filter(HrZoneConfig.user_id == user.id)
        .order_by(HrZoneConfig.valid_from.desc(), HrZoneConfig.id.desc())
        .all()
    )
    return HrZonesHistoryOut(
        metrics=[
            MetricHistoryOut(
                kind=row.kind, value=row.value_bpm, source=row.source,
                valid_from=row.valid_from,
            )
            for row in metric_rows
        ],
        configs=[
            ConfigHistoryOut(
                method=row.method, bounds=row.bounds, valid_from=row.valid_from
            )
            for row in config_rows
        ],
    )


@router.get("/garmin-connection")
def get_garmin_connection(
    user: User = Depends(require_session),
    db: Session = Depends(get_db),
) -> ConnectionOut:
    """GTDB-16: estado da conexão Garmin do usuário da sessão — só
    exibição, sem ação (re-login é CLI do operador). A derivação pura
    (3 estados, emenda incluída) vive no service; a resposta carrega
    apenas metadados (GTDB-17). 401 sem sessão é dado pelo include no
    main."""
    state, tokens_updated_at = service.garmin_connection(db, user.id)
    return ConnectionOut(state=state, tokens_updated_at=tokens_updated_at)
