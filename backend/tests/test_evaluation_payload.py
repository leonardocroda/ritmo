"""Payload determinístico da avaliação — integração com DB semeados (EVAL-02/07/16).

Valores afirmados são literais derivados das fixtures com aritmética
exata (lições L-001/L-002): 4 voltas easy de 300s + 1 repetition de 220s
→ easy 1200/1420 = 84,5% · repetition 220/1420 = 15,5% (denominador
único = duração das voltas com zona). O vdot pinado (50,2) vem do
arquivo calibrado vigente — mesmo acoplamento dos cuts de zona da suite
(test_activities_api).

Nenhum teste aqui chama o Garmin: dados semeados direto no banco (AD-002).
"""

from datetime import date, datetime

import pytest
from sqlalchemy import select

from app.activities import service
from app.core.config import Settings
from app.db.engine import SessionLocal, init_db
from app.db.models import (
    Activity,
    DailyLoad,
    HrZoneConfig,
    Hrv,
    Pattern,
    PersonalRecord,
    Rhr,
    Sleep,
    Split,
    User,
    UserHrMetric,
)
from app.evaluation.payload import build_evaluation_payload
from app.vdot.zones import load_zone_config

EASY_PACE_S = 300.0   # 5:00/km -> easy (cut easy/marathon = 4:41)
REPETITION_PACE_S = 220.0  # 3:40/km -> repetition (cut interval/repetition = 3:45)
DAY = date(2024, 1, 15)
START = datetime(2024, 1, 15, 7, 0, 0)


@pytest.fixture(autouse=True)
def _clean_eval_env(monkeypatch):
    """Isola LTHR e caminho das zonas de env do host."""
    monkeypatch.delenv("LTHR_BPM", raising=False)
    monkeypatch.delenv("VDOT_ZONES_PATH", raising=False)


@pytest.fixture()
def db():
    """Schema criado pelo init_db (o conftest derruba antes de cada teste)."""
    init_db()
    with SessionLocal() as session:
        yield session


@pytest.fixture()
def settings() -> Settings:
    return Settings(_env_file=None)


@pytest.fixture()
def zone_config(settings: Settings):
    return load_zone_config(settings.vdot_zones_path)


def _seed_activity(db, *, name: str = "Easy Run", distance_m: float = 5000.0,
                   duration_s: float = 1420.0, feel: int | None = 3,
                   rpe: int | None = 4, avg_cadence: float | None = 170.0,
                   elevation_gain_m: float | None = 55.0,
                   aerobic_te: float | None = 2.8, anaerobic_te: float | None = 0.4,
                   training_load: float | None = 120.0) -> Activity:
    # user-scope: usuário dono da atividade (o payload lê por activity.user_id)
    user = User(display_name="Corredora")
    db.add(user)
    db.flush()
    activity = Activity(
        user_id=user.id,
        garmin_id=f"payload-{name}-{distance_m}-{duration_s}",
        start_time=START,
        activity_type="running",
        name=name,
        distance_m=distance_m,
        duration_s=duration_s,
        avg_hr=145,
        max_hr=165,
        avg_cadence=avg_cadence,
        elevation_gain_m=elevation_gain_m,
        aerobic_te=aerobic_te,
        anaerobic_te=anaerobic_te,
        training_load=training_load,
        feel=feel,
        rpe=rpe,
    )
    db.add(activity)
    db.flush()
    return activity


def _seed_split(db, activity_id: int, idx: int, *, dist_m: float = 1000.0,
                duration_s: float = 300.0, avg_hr: int = 142,
                avg_temperature: float | None = 22.0,
                avg_cadence: float | None = 165.0,
                elevation_m: float | None = 12.5) -> None:
    db.add(
        Split(
            activity_id=activity_id,
            idx=idx,
            dist_m=dist_m,
            duration_s=duration_s,
            pace_s=duration_s * 1000 / dist_m,
            avg_hr=avg_hr,
            avg_cadence=avg_cadence,
            avg_temperature=avg_temperature,
            elevation_m=elevation_m,
        )
    )


def _seed_day(db, user_id: int) -> None:
    """Sono/HRV/RHR/PMC da data do treino + PRs + padrão ativo — do dono."""
    db.add(Sleep(user_id=user_id, date=DAY, duration_s=28800.0, score=85))
    db.add(Hrv(user_id=user_id, date=DAY, value=45.0, status="BALANCED"))
    db.add(Rhr(user_id=user_id, date=DAY, value=43))
    db.add(DailyLoad(user_id=user_id, date=DAY, ctl=132.2, atl=141.3, tsb=-9.2, acwr=1.1))
    db.add(PersonalRecord(user_id=user_id, event="FASTEST_5K", value=1163.83, pr_date=date(2026, 4, 26)))
    db.add(PersonalRecord(user_id=user_id, event="FASTEST_10K", value=2447.0, pr_date=None))
    db.add(PersonalRecord(user_id=user_id, event="LONGEST_RUN", value=32000.0, pr_date=date(2024, 1, 1)))
    db.add(
        Pattern(
            user_id=user_id,
            name="km1_rapido",
            trigger="largadas de prova",
            description="km 1 mais rápido que a média em 100% das provas máximas",
        )
    )
    db.flush()


def _payload(db, activity, settings, zone_config, *, intent_type: str,
             intent_text: str | None = None) -> dict:
    detail = service.get_activity_detail(db, activity.id, activity.user_id, zone_config)
    return build_evaluation_payload(
        db, activity, activity.user_id, detail, intent_type, intent_text, settings
    )


def test_payload_completo_blocos_e_matematica_exata(db, settings, zone_config) -> None:
    """EVAL-02: todos os blocos com dado; % por zona e zona alvo pinados."""
    activity = _seed_activity(db)
    for idx in range(1, 5):
        _seed_split(db, activity.id, idx, duration_s=300.0)
    _seed_split(db, activity.id, 5, duration_s=220.0, avg_hr=150)
    _seed_day(db, activity.user_id)
    db.commit()

    payload = _payload(db, activity, settings, zone_config,
                       intent_type="facil", intent_text="era pra ser 30min a 4:15")

    # Blocos sempre presentes + blocos com dado (EVAL-02)
    for key in (
        "intencao", "resumo", "voltas", "tempo_por_zona_pct", "zona_alvo",
        "contexto", "carga_do_dia", "zonas", "vdot", "lthr_bpm", "prs", "padroes",
    ):
        assert key in payload, f"bloco {key} ausente"

    assert payload["intencao"] == {"tipo": "facil", "texto": "era pra ser 30min a 4:15"}

    # Resumo completo — TODOS os campos, por valor literal (EVAL-02:
    # deletar qualquer um do payload.py tem que falhar aqui)
    assert payload["resumo"] == {
        "nome": "Easy Run",
        "data": "2024-01-15",
        "distancia_km": 5.0,
        "duracao": "23:40",
        "pace_medio": "4:44/km",
        "fc_media": 145,
        "fc_max": 165,
        "cadencia_media": 170.0,
        "elevacao_gain_m": 55.0,
        "te_aerobico": 2.8,
        "te_anaerobico": 0.4,
        "carga_treino": 120.0,
        "feel": 3,
        "rpe": 4,
    }

    # Aritmética exata: denominador 1420s, easy 1200s, repetition 220s
    assert payload["tempo_por_zona_pct"] == {
        "easy": 84.5, "marathon": 0.0, "threshold": 0.0, "interval": 0.0,
        "repetition": 15.5,
    }
    assert sum(payload["tempo_por_zona_pct"].values()) == 100.0
    assert payload["zona_alvo"] == {"zonas": ["easy"], "pct_zona_alvo": 84.5}

    # Voltas classificadas — TODOS os campos da 1ª volta, por valor (EVAL-02)
    voltas = payload["voltas"]
    assert len(voltas) == 5
    assert voltas[0] == {
        "km": "1,0",
        "duracao_s": 300.0,
        "pace": "5:00/km",
        "zona": "easy",
        "fc": 142,
        "cadencia": 165.0,
        "temperatura_c": 22.0,
        "elevacao_m": 12.5,
    }
    assert voltas[4]["km"] == "5,0" and voltas[4]["zona"] == "repetition"
    assert voltas[4]["pace"] == "3:40/km"

    # Contexto do dia — só o que existir, chaves PT-BR
    assert payload["contexto"]["sono"] == {"duracao_s": 28800.0, "score": 85}
    assert payload["contexto"]["hrv"] == {"valor": 45.0, "status": "BALANCED"}
    assert payload["contexto"]["fc_repouso"] == {"bpm": 43}
    assert payload["contexto"]["temperatura_c"] == 22.0

    # PMC do dia, valores exatos da linha
    assert payload["carga_do_dia"] == {"ctl": 132.2, "atl": 141.3, "tsb": -9.2, "acwr": 1.1}

    # PRs: só canônico com data; VDOT do arquivo calibrado; LTHR da config
    assert payload["prs"] == [{"evento": "5K", "tempo_s": 1163.83, "data": "2026-04-26"}]
    assert payload["vdot"] == {"valor": 50.2, "fonte": "10K em 41:15", "data_teste": "2026-10-03"}
    assert payload["lthr_bpm"] == 177

    # Padrões ativos alimentam o prompt (plano §9.3)
    assert payload["padroes"] == [
        {
            "nome": "km1_rapido",
            "gatilho": "largadas de prova",
            "descricao": "km 1 mais rápido que a média em 100% das provas máximas",
        }
    ]

    # Zonas vigentes para o LLM — rótulo e faixa, nunca a cor (UI)
    zonas = payload["zonas"]
    assert len(zonas) == 5
    assert all({"zona", "rotulo", "faixa"} == set(z) for z in zonas)

    # Corrida de 5km: consistência fica fora do payload (gate >=8km — spec)
    assert "consistencia" not in payload


def test_progressivo_e_prova_sem_zona_alvo(db, settings, zone_config) -> None:
    """EVAL-02: progressivo e prova não têm zona alvo única (assumption)."""
    activity = _seed_activity(db)
    for idx in range(1, 5):
        _seed_split(db, activity.id, idx)
    db.commit()
    for intent in ("progressivo", "prova"):
        payload = _payload(db, activity, settings, zone_config, intent_type=intent)
        assert "zona_alvo" not in payload
        # a distribuição por zona continua no payload p/ o LLM julgar
        assert payload["tempo_por_zona_pct"]["easy"] == 100.0


@pytest.mark.parametrize(
    ("intent_type", "expected_zones"),
    [
        ("facil", ["easy"]),
        ("tempo", ["threshold"]),
        ("limiar", ["threshold"]),
        ("intervalado", ["interval"]),
        ("longao", ["easy", "marathon"]),
        ("progressivo", None),
        ("prova", None),
    ],
)
def test_zona_alvo_por_intencao_mapa_completo(
    db, settings, zone_config, intent_type, expected_zones
) -> None:
    """EVAL-02 (gap do Verifier, Fix 2): o mapa de zonas alvo cobre as
    7 intenções — mutar qualquer entrada (ex.: tempo→easy) falha aqui."""
    activity = _seed_activity(db)
    for idx in range(1, 5):
        _seed_split(db, activity.id, idx)
    db.commit()
    payload = _payload(db, activity, settings, zone_config, intent_type=intent_type)
    if expected_zones is None:
        assert "zona_alvo" not in payload
    else:
        assert payload["zona_alvo"]["zonas"] == expected_zones


def test_sem_voltas_payload_honesto(db, settings, zone_config) -> None:
    """EVAL-16: sem voltas, blocos de voltas/zona são omitidos e a
    avaliação prossegue com os agregados."""
    activity = _seed_activity(db, distance_m=5000.0, duration_s=1500.0)
    db.commit()
    payload = _payload(db, activity, settings, zone_config, intent_type="facil")
    for key in ("voltas", "tempo_por_zona_pct", "zona_alvo", "consistencia"):
        assert key not in payload
    assert payload["resumo"]["pace_medio"] == "5:00/km"  # 1500s/5km
    assert payload["intencao"] == {"tipo": "facil", "texto": None}


def test_carga_do_dia_e_contexto_omitidos_sem_dado(db, settings, zone_config) -> None:
    """EVAL-02: sem linha de PMC e sem sono/HRV/RHR, blocos somem."""
    activity = _seed_activity(db)
    for idx in range(1, 5):
        _seed_split(db, activity.id, idx, avg_temperature=None)
    db.commit()
    payload = _payload(db, activity, settings, zone_config, intent_type="facil")
    assert "carga_do_dia" not in payload
    assert "contexto" not in payload
    assert "prs" not in payload
    assert "padroes" not in payload


def test_consistencia_passthrough_com_gate_e_longao(db, settings, zone_config) -> None:
    """EVAL-02: com >=8km e >=4 voltas a consistência entra; longão alvo
    easy∪marathon fecha 100% com voltas easy."""
    activity = _seed_activity(db, name="Longao", distance_m=8000.0, duration_s=2400.0)
    for idx in range(1, 9):
        _seed_split(db, activity.id, idx)
    db.commit()
    payload = _payload(db, activity, settings, zone_config, intent_type="longao")

    consistency = payload["consistencia"]
    assert consistency["first_half_pace_s"] == 300.0
    assert consistency["second_half_pace_s"] == 300.0
    assert consistency["balance_delta_s"] == 0.0

    assert payload["zona_alvo"] == {"zonas": ["easy", "marathon"], "pct_zona_alvo": 100.0}
    assert payload["tempo_por_zona_pct"]["easy"] == 100.0


def test_payload_nao_importa_gateway_garmin() -> None:
    """EVAL-07: o payload lê só do banco — nenhum import do gateway Garmin."""
    from pathlib import Path

    source = Path("app/evaluation/payload.py").read_text(encoding="utf-8")
    assert "app.garmin" not in source
    assert "garminconnect" not in source


# ---------------------------------------------------------------
# hr-zones T9 — lthr do perfil + bloco zonas_fc (HRZ-17/18/19)
# ---------------------------------------------------------------

# Defaults lthr do spec (HRZ-08) — literais do teste (L-001)
LTHR_BOUNDS = [
    {"low": 65, "high": 80},
    {"low": 80, "high": 89},
    {"low": 89, "high": 95},
    {"low": 95, "high": 100},
    {"low": 100, "high": None},
]


def _seed_fclthr(db, user_id: int, value: int, valid_from: date) -> None:
    """Linha de métrica fclthr (série effective-dated do hr-zones)."""
    db.add(
        UserHrMetric(
            user_id=user_id, kind="fclthr", value_bpm=value,
            source="manual", valid_from=valid_from,
        )
    )


def _seed_lthr_config(db, user_id: int) -> None:
    """Config de zonas lthr com os defaults, vigente antes do treino."""
    db.add(
        HrZoneConfig(
            user_id=user_id, method="lthr",
            bounds={"zones": LTHR_BOUNDS}, valid_from=date(2024, 1, 1),
        )
    )


def test_lthr_bpm_da_metrica_vigente_na_data_do_treino(db, settings, zone_config) -> None:
    """HRZ-17/12: lthr_bpm vem da métrica fclthr vigente NA DATA do
    treino — mudança posterior não muda o treino antigo."""
    activity = _seed_activity(db)
    _seed_fclthr(db, activity.user_id, 172, date(2024, 1, 1))
    _seed_fclthr(db, activity.user_id, 185, date(2024, 2, 1))
    db.commit()

    payload = _payload(db, activity, settings, zone_config, intent_type="facil")
    assert payload["lthr_bpm"] == 172  # vigente em 2024-01-15, não a de fevereiro


def test_lthr_bpm_fallback_do_env_sem_metrica(db, zone_config) -> None:
    """HRZ-17: sem métrica fclthr, o fallback é o env (LTHR_BPM) —
    ramo pinado com valor distinto do default."""
    custom = Settings(_env_file=None, lthr_bpm=181)
    activity = _seed_activity(db)
    db.commit()

    payload = _payload(db, activity, custom, zone_config, intent_type="facil")
    assert payload["lthr_bpm"] == 181


def test_zonas_fc_tempo_por_zona_exato(db, settings, zone_config) -> None:
    """HRZ-18: bloco zonas_fc com as zonas em bpm e tempo/pct por zona
    exatos — denominador único = duração das voltas COM FC (a volta sem
    FC fica fora, mesma convenção do bloco de pace)."""
    activity = _seed_activity(db)
    _seed_lthr_config(db, activity.user_id)
    _seed_fclthr(db, activity.user_id, 172, date(2024, 1, 1))
    # fclthr 172 nos defaults lthr -> 112/138/153/163/172 (Z5 aberta)
    _seed_split(db, activity.id, 1, duration_s=300.0, avg_hr=130)  # Z1
    _seed_split(db, activity.id, 2, duration_s=300.0, avg_hr=145)  # Z2
    _seed_split(db, activity.id, 3, duration_s=300.0, avg_hr=155)  # Z3
    _seed_split(db, activity.id, 4, duration_s=120.0, avg_hr=165)  # Z4
    _seed_split(db, activity.id, 5, duration_s=60.0, avg_hr=180)  # Z5 aberta
    _seed_split(db, activity.id, 6, duration_s=60.0, avg_hr=None)  # sem FC: fora
    db.commit()

    payload = _payload(db, activity, settings, zone_config, intent_type="facil")
    # 1080s de voltas com FC (3×300 + 120 + 60): 300/1080=27,8 · 120/1080=11,1 · 60/1080=5,6
    assert payload["zonas_fc"] == {
        "zonas": [
            {"n": 1, "low": 112, "high": 138},
            {"n": 2, "low": 138, "high": 153},
            {"n": 3, "low": 153, "high": 163},
            {"n": 4, "low": 163, "high": 172},
            {"n": 5, "low": 172, "high": None},
        ],
        "tempo_por_zona": [
            {"zona": 1, "segundos": 300.0, "pct": 27.8},
            {"zona": 2, "segundos": 300.0, "pct": 27.8},
            {"zona": 3, "segundos": 300.0, "pct": 27.8},
            {"zona": 4, "segundos": 120.0, "pct": 11.1},
            {"zona": 5, "segundos": 60.0, "pct": 5.6},
        ],
    }


def test_zonas_fc_usa_zonas_da_epoca_do_treino(db, settings, zone_config) -> None:
    """HRZ-12 no payload: métrica mudada DEPOIS do treino não reclassifica
    o treino antigo — zonas da época (fclthr 172, não a de depois)."""
    activity = _seed_activity(db)
    _seed_lthr_config(db, activity.user_id)
    _seed_fclthr(db, activity.user_id, 172, date(2024, 1, 1))
    _seed_fclthr(db, activity.user_id, 180, date(2024, 2, 1))
    _seed_split(db, activity.id, 1, avg_hr=130)  # Z1 com fclthr 172
    db.commit()

    payload = _payload(db, activity, settings, zone_config, intent_type="facil")
    zonas_fc = payload["zonas_fc"]
    assert zonas_fc["zonas"][0] == {"n": 1, "low": 112, "high": 138}  # 172, não 180
    assert zonas_fc["tempo_por_zona"][0] == {"zona": 1, "segundos": 300.0, "pct": 100.0}
    assert payload["lthr_bpm"] == 172


def test_zonas_fc_omitido_sem_fc_nas_voltas(db, settings, zone_config) -> None:
    """HRZ-19: nenhuma volta com FC -> bloco zonas_fc omitido (nenhum
    número inventado — mesma postura do bloco de pace)."""
    activity = _seed_activity(db)
    _seed_lthr_config(db, activity.user_id)
    _seed_fclthr(db, activity.user_id, 172, date(2024, 1, 1))
    _seed_split(db, activity.id, 1, avg_hr=None)
    _seed_split(db, activity.id, 2, avg_hr=None)
    db.commit()

    payload = _payload(db, activity, settings, zone_config, intent_type="facil")
    assert "zonas_fc" not in payload
    assert payload["lthr_bpm"] == 172  # o lthr chega mesmo sem o bloco


def test_zonas_fc_omitido_sem_config_ou_sem_metrica(db, settings, zone_config) -> None:
    """HRZ-19/11: zonas inexistentes (sem config, ou config sem a métrica
    exigida pelo método) -> bloco omitido."""
    # sem config nenhuma (usuário novo não tem hr_zone_configs)
    activity = _seed_activity(db)
    _seed_split(db, activity.id, 1)
    db.commit()
    payload = _payload(db, activity, settings, zone_config, intent_type="facil")
    assert "zonas_fc" not in payload

    # com config lthr mas sem fclthr: zonas null (HRZ-11) -> bloco omitido
    activity2 = _seed_activity(db, name="Com Config", distance_m=6000.0)
    _seed_lthr_config(db, activity2.user_id)
    _seed_split(db, activity2.id, 1)
    db.commit()
    payload2 = _payload(db, activity2, settings, zone_config, intent_type="facil")
    assert "zonas_fc" not in payload2
