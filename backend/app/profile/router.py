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
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.deps import require_session
from app.db.engine import get_db
from app.db.models import HrZoneConfig, User, UserHrMetric, VdotZoneConfig
from app.profile import calc, service
from app.vdot.daniels import calculate_vdot, equivalent_time, pace_for_fraction

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


# =============================================================================
# Pace Zones (VDOT) — feature pace-zones
# =============================================================================


class PaceZoneOut(BaseModel):
    key: Literal["easy", "marathon", "threshold", "interval", "repetition"]
    pace_range: str | None = None
    pace: str | None = None
    ms_min: float | None = None
    ms_max: float | None = None
    ms: float | None = None
    description: str


class PaceZonesOut(BaseModel):
    vdot: float
    source: str
    test_date: date
    distancia_metros: float
    tempo_segundos: float
    zones: dict[str, PaceZoneOut]
    equivalencias: dict[str, str]


# =============================================================================
# VDOT Recalibration — POST /api/profile/pace-zones/recalibrate
# =============================================================================

# Distâncias de teste padrão (em km) — espelha calibrate_vdot.py
STANDARD_TEST_DISTANCES_KM = {
    "1500m": 1.5,
    "3K": 3.0,
    "5K": 5.0,
    "10K": 10.0,
    "Meia Maratona": 21.0975,
    "Maratona": 42.195,
}

# Distâncias de prova para equivalências (em km) — espelha calibrate_vdot.py
RACE_DISTANCES_KM = {
    "5K": 5.0,
    "10K": 10.0,
    "Meia Maratona": 21.0975,
    "Maratona": 42.195,
}


def format_pace(seconds_per_km: float) -> str:
    """Converte segundos por km para formato min:sec/km."""
    seconds = max(0, int(round(seconds_per_km)))
    minutes, secs = divmod(seconds, 60)
    return f"{minutes}:{secs:02d}/km"


def min_km_to_ms(seconds_per_km: float) -> float:
    """Converte segundos por km para m/s."""
    return round(1000 / seconds_per_km, 3)


def gerar_zonas(vdot: float) -> dict:
    """
    Gera as 5 zonas de ritmo a partir do VDOT.
    Espelha a função gerar_zonas de calibrate_vdot.py.
    """
    zonas = {}

    # Easy: 59-74% do VDOT
    e_slow = pace_for_fraction(vdot, 0.59)
    e_fast = pace_for_fraction(vdot, 0.74)
    zonas["easy"] = {
        "pace_range": f"{format_pace(e_slow)}-{format_pace(e_fast)}",
        "ms_min": min_km_to_ms(e_slow),
        "ms_max": min_km_to_ms(e_fast),
        "description": "Recuperação, base aeróbica, aquecimento/desaquecimento",
    }

    # Marathon: derivado do ritmo equivalente de maratona
    marathon_seconds = equivalent_time(vdot, RACE_DISTANCES_KM["Maratona"])
    m_pace = marathon_seconds / RACE_DISTANCES_KM["Maratona"]
    zonas["marathon"] = {
        "pace": format_pace(m_pace),
        "ms": min_km_to_ms(m_pace),
        "description": "Ritmo de maratona, longões",
    }

    # Threshold: 83-88% do VDOT
    t_fast = pace_for_fraction(vdot, 0.88)
    t_slow = pace_for_fraction(vdot, 0.83)
    zonas["threshold"] = {
        "pace_range": f"{format_pace(t_fast)}-{format_pace(t_slow)}",
        "ms_min": min_km_to_ms(t_slow),
        "ms_max": min_km_to_ms(t_fast),
        "description": "Limiar de lactato, tempo runs",
    }

    # Interval: 95-100% do VDOT
    i_fast = pace_for_fraction(vdot, 1.00)
    i_slow = pace_for_fraction(vdot, 0.95)
    zonas["interval"] = {
        "pace_range": f"{format_pace(i_slow)}-{format_pace(i_fast)}",
        "ms_min": min_km_to_ms(i_slow),
        "ms_max": min_km_to_ms(i_fast),
        "description": "VO2max, esforços de 2-4 min",
    }

    # Repetition: ~105% do VDOT
    r_pace = pace_for_fraction(vdot, 1.05)
    zonas["repetition"] = {
        "pace": format_pace(r_pace),
        "ms": min_km_to_ms(r_pace),
        "description": "Repetições curtas, 800m-1km",
    }

    return zonas


class RecalibrateIn(BaseModel):
    """Entrada para recalibração de VDOT via API."""
    distance_km: float = Field(..., gt=0, description="Distância do teste em km")
    time_str: str = Field(..., description="Tempo total no formato HH:MM:SS ou MM:SS")
    test_date: str | None = Field(None, description="Data do teste (AAAA-MM-DD), default hoje")


def parse_time_str(time_str: str) -> int:
    """Converte HH:MM:SS ou MM:SS para segundos totais. Levanta ValueError se inválido."""
    partes = time_str.strip().split(":")
    if len(partes) == 3:
        try:
            horas = int(partes[0])
            minutos = int(partes[1])
            segundos = int(partes[2])
            if horas < 0 or minutos < 0 or minutos >= 60 or segundos < 0 or segundos >= 60:
                raise ValueError
            return horas * 3600 + minutos * 60 + segundos
        except ValueError:
            raise ValueError("formato inválido, use HH:MM:SS")
    elif len(partes) == 2:
        try:
            minutos = int(partes[0])
            segundos = int(partes[1])
            if minutos < 0 or segundos < 0 or segundos >= 60:
                raise ValueError
            return minutos * 60 + segundos
        except ValueError:
            raise ValueError("formato inválido, use MM:SS")
    else:
        raise ValueError("formato inválido, use HH:MM:SS ou MM:SS")


def calculate_equivalencias(vdot: float) -> dict:
    """Calcula tempos equivalentes para distâncias de prova padrão."""
    equivalencias = {}
    for label, dist_km in RACE_DISTANCES_KM.items():
        pred_seconds = equivalent_time(vdot, dist_km)
        equivalencias[label] = format_pace(pred_seconds / dist_km)
    return equivalencias


@router.post("/pace-zones/recalibrate")
def recalibrate_pace_zones(
    payload: RecalibrateIn,
    user: User = Depends(require_session),
    db: Session = Depends(get_db),
) -> PaceZonesOut:
    """Recalibra zonas de ritmo (VDOT) a partir de distância e tempo de teste.

    Body: { distance_km, time_str (HH:MM:SS), test_date? }
    Retorna PaceZonesOut atualizado. 422 se entrada inválida.
    """
    # Validar e converter tempo
    try:
        total_seconds = parse_time_str(payload.time_str)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"time_str: {exc}") from exc

    if total_seconds <= 0:
        raise HTTPException(status_code=422, detail="time_str: tempo deve ser maior que zero")

    # Validar distância
    if payload.distance_km <= 0:
        raise HTTPException(status_code=422, detail="distance_km: deve ser maior que 0")

    # Data do teste
    if payload.test_date:
        try:
            test_date = date.fromisoformat(payload.test_date)
            if test_date > date.today():
                raise HTTPException(status_code=422, detail="test_date: não pode ser no futuro")
        except ValueError:
            raise HTTPException(status_code=422, detail="test_date: formato inválido, use AAAA-MM-DD")
    else:
        test_date = date.today()

    # Calcular VDOT
    distancia_metros = payload.distance_km * 1000
    vdot = round(calculate_vdot(distancia_metros, total_seconds), 1)

    # Gerar zonas
    zonas = gerar_zonas(vdot)

    # Calcular equivalências
    equivalencias = calculate_equivalencias(vdot)

    # Fonte legível
    source = f"{payload.distance_km:.3f}km em {payload.time_str}"

    # Salvar no banco (upsert)
    existing = (
        db.query(VdotZoneConfig)
        .filter(VdotZoneConfig.user_id == user.id)
        .first()
    )

    # Adicionar key a cada zona para o response
    zones_with_key = {}
    for key, zone in zonas.items():
        zone_copy = dict(zone)
        zone_copy["key"] = key
        zones_with_key[key] = zone_copy

    if existing:
        existing.vdot = vdot
        existing.source = source
        existing.test_date = test_date
        existing.distance_m = distancia_metros
        existing.time_s = total_seconds
        existing.zones = zonas
        existing.equivalencias = equivalencias
        existing.valid_from = test_date
    else:
        new_config = VdotZoneConfig(
            user_id=user.id,
            vdot=vdot,
            source=source,
            test_date=test_date,
            distance_m=distancia_metros,
            time_s=total_seconds,
            zones=zonas,
            equivalencias=equivalencias,
            valid_from=test_date,
        )
        db.add(new_config)

    db.commit()

    return PaceZonesOut(
        vdot=vdot,
        source=source,
        test_date=test_date,
        distancia_metros=distancia_metros,
        tempo_segundos=total_seconds,
        zones=zones_with_key,
        equivalencias=equivalencias,
    )


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


@router.get("/pace-zones")
def get_pace_zones(
    user: User = Depends(require_session),
    db: Session = Depends(get_db),
) -> PaceZonesOut:
    """Retorna as zonas de ritmo (VDOT) do usuário logado.

    Inclui: VDOT, fonte, data do teste, distância, tempo, 5 zonas
    (com pace range/pace, ms_min/ms_max/ms, descrição) e equivalências
    de prova. 500 se não houver configuração para o usuário.
    """
    config = (
        db.query(VdotZoneConfig)
        .filter(VdotZoneConfig.user_id == user.id)
        .order_by(VdotZoneConfig.valid_from.desc(), VdotZoneConfig.id.desc())
        .first()
    )
    if config is None:
        raise HTTPException(
            status_code=500, detail="zonas VDOT não configuradas"
        )

    # Adicionar key a cada zona (o JSON no banco não tem key dentro de cada zona)
    zones_with_key = {}
    for key, zone in config.zones.items():
        zone_copy = dict(zone)
        zone_copy["key"] = key
        zones_with_key[key] = zone_copy

    return PaceZonesOut(
        vdot=config.vdot,
        source=config.source,
        test_date=config.test_date,
        distancia_metros=config.distance_m,
        tempo_segundos=config.time_s,
        zones=zones_with_key,
        equivalencias=config.equivalencias,
    )
