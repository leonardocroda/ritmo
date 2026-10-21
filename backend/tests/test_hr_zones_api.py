"""API de zonas de FC (T5, feature hr-zones) — HTTP no Postgres real.

Rotas em escopo (matriz): happy + 422 por campo + 401 sem sessão +
isolamento A×B — com `session_client` (sessão real por usuário; o
conftest semeia o usuário, os testes o user_id devolvido). O usuário de
teste tem id > 1: o seed lthr da T3 é só do usuário 1, então o estado
inicial de métricas/config é honestamente vazio. Valores afirmados são
literais do spec (HRZ-08/10) — nunca importados da implementação.
"""

from datetime import date

from app.auth.security import hash_password
from app.auth.service import create_session
from app.db.engine import SessionLocal
from app.db.models import HrZoneConfig, User, UserHrMetric

TODAY = date.today()
TODAY_ISO = TODAY.isoformat()

LTHR_DEFAULTS = {
    "zones": [
        {"low": 65, "high": 80},
        {"low": 80, "high": 89},
        {"low": 89, "high": 95},
        {"low": 95, "high": 100},
        {"low": 100, "high": None},
    ]
}
FCR_DEFAULTS = {
    "zones": [
        {"low": 50, "high": 60},
        {"low": 60, "high": 70},
        {"low": 70, "high": 80},
        {"low": 80, "high": 90},
        {"low": 90, "high": 100},
    ]
}
FCMAX_DEFAULTS = {
    "zones": [
        {"low": 50, "high": 60},
        {"low": 60, "high": 70},
        {"low": 70, "high": 80},
        {"low": 80, "high": 90},
        {"low": 90, "high": 100},
    ]
}


def _seed_metric(db, user_id: int, kind: str, value: int, source: str, valid_from) -> None:
    db.add(
        UserHrMetric(
            user_id=user_id, kind=kind, value_bpm=value, source=source,
            valid_from=valid_from,
        )
    )


def _seed_config(db, user_id: int, method: str, bounds: dict, valid_from) -> None:
    db.add(
        HrZoneConfig(
            user_id=user_id, method=method, bounds=bounds, valid_from=valid_from
        )
    )


def _new_user_with_token(db, email: str) -> tuple[User, str]:
    user = User(
        display_name="Outra",
        email=email,
        password_hash=hash_password("senha-segura-123"),
    )
    db.add(user)
    db.flush()
    token = create_session(db, user.id)
    db.commit()
    return user, token


# ---------------------------------------------------------------
# GET /api/profile/hr-zones (HRZ-01/10/11)
# ---------------------------------------------------------------


def test_get_hr_zones_full_shape(session_client) -> None:
    """HRZ-01/10: com sessão, o shape completo — métrica com
    {value, source, valid_from}, config vigente, zonas derivadas em bpm
    (fclthr 177 lthr → [115, 142, 158, 168, 177+]) e defaults dos 3
    métodos para prefill."""
    client, user_id = session_client
    with SessionLocal() as db:
        _seed_metric(db, user_id, "fclthr", 177, "manual", TODAY)
        _seed_config(db, user_id, "lthr", LTHR_DEFAULTS, TODAY)
        db.commit()

    response = client.get("/api/profile/hr-zones")
    assert response.status_code == 200
    body = response.json()

    assert body["metrics"] == {
        "fcmax": None,
        "fcrest": None,
        "fclthr": {"value": 177, "source": "manual", "valid_from": TODAY_ISO},
    }
    assert body["config"] == {
        "method": "lthr", "bounds": LTHR_DEFAULTS, "valid_from": TODAY_ISO,
    }
    assert body["zones"] == [
        {"n": 1, "low": 115, "high": 142},
        {"n": 2, "low": 142, "high": 158},
        {"n": 3, "low": 158, "high": 168},
        {"n": 4, "low": 168, "high": 177},
        {"n": 5, "low": 177, "high": None},
    ]
    assert body["defaults"] == {
        "lthr": LTHR_DEFAULTS["zones"],
        "fcr": FCR_DEFAULTS["zones"],
        "fcmax": FCMAX_DEFAULTS["zones"],
    }


def test_get_hr_zones_empty_state(session_client) -> None:
    """HRZ-01/11: nunca configurado -> métricas null, config null,
    zonas null (estado vazio honesto) e defaults presentes."""
    client, _user_id = session_client

    response = client.get("/api/profile/hr-zones")
    assert response.status_code == 200
    body = response.json()

    assert body["metrics"] == {"fcmax": None, "fcrest": None, "fclthr": None}
    assert body["config"] is None
    assert body["zones"] is None
    assert set(body["defaults"]) == {"lthr", "fcr", "fcmax"}


# ---------------------------------------------------------------
# PUT /api/profile/hr-zones (HRZ-02/03/04/08/09)
# ---------------------------------------------------------------


def test_put_metric_creates_manual_row_and_is_idempotent(session_client) -> None:
    """HRZ-02/03: PUT de métrica cria linha manual com valid_from hoje;
    repetido (valor igual) responde sucesso SEM linha nova; a resposta
    tem o shape do GET."""
    client, user_id = session_client

    response = client.put(
        "/api/profile/hr-zones", json={"metrics": {"fclthr": 185}}
    )
    assert response.status_code == 200
    assert response.json()["metrics"]["fclthr"] == {
        "value": 185, "source": "manual", "valid_from": TODAY_ISO,
    }

    with SessionLocal() as db:
        rows = db.query(UserHrMetric).filter(UserHrMetric.user_id == user_id).all()
        assert len(rows) == 1
        assert (rows[0].value_bpm, rows[0].source, rows[0].valid_from) == (
            185, "manual", TODAY,
        )

    repeat = client.put("/api/profile/hr-zones", json={"metrics": {"fclthr": 185}})
    assert repeat.status_code == 200
    assert repeat.json()["metrics"]["fclthr"]["value"] == 185

    with SessionLocal() as db:
        assert db.query(UserHrMetric).filter(UserHrMetric.user_id == user_id).count() == 1


def test_put_metrics_validation_422_per_field(session_client) -> None:
    """HRZ-04: fora dos limites ou incoerente -> 422 apontando o campo e
    o motivo (PT-BR), sem gravar nada."""
    client, user_id = session_client
    cases = [
        ({"metrics": {"fcmax": 99}}, "fcmax: deve estar entre 100 e 230 bpm"),
        ({"metrics": {"fcmax": 231}}, "fcmax: deve estar entre 100 e 230 bpm"),
        ({"metrics": {"fcrest": 29}}, "fcrest: deve estar entre 30 e 110 bpm"),
        ({"metrics": {"fclthr": 95}}, "fclthr: deve estar entre 100 e 220 bpm"),
        # incoerência cross-field dentro da própria chamada (HRZ-04 edge)
        ({"metrics": {"fcmax": 190, "fclthr": 195}},
         "fclthr: limiar acima da FC máxima"),
    ]
    for payload, detail in cases:
        response = client.put("/api/profile/hr-zones", json=payload)
        assert response.status_code == 422, payload
        assert response.json()["detail"] == detail, payload

    with SessionLocal() as db:
        assert db.query(UserHrMetric).filter(UserHrMetric.user_id == user_id).count() == 0


def test_put_incoherence_uses_vigente_fcmax_from_history(session_client) -> None:
    """HRZ-04 via merge: fcmax vigente 190 + update fclthr 195 ->
    incoerente com a linha NOVA contra a VIGENTE (valida o conjunto, não
    só o payload)."""
    client, user_id = session_client
    assert client.put(
        "/api/profile/hr-zones", json={"metrics": {"fcmax": 190}}
    ).status_code == 200

    response = client.put(
        "/api/profile/hr-zones", json={"metrics": {"fclthr": 195}}
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "fclthr: limiar acima da FC máxima"


def test_put_empty_or_valueless_body_422(session_client) -> None:
    """PUT sem nenhum campo efetivo -> 422 'nada para atualizar'
    (design §Erros); bounds sem método e sem config vigente -> 422."""
    client, _user_id = session_client

    for payload in ({}, {"metrics": {}}, {"metrics": {"fcmax": None}}):
        response = client.put("/api/profile/hr-zones", json=payload)
        assert response.status_code == 422, payload
        assert response.json()["detail"] == "nada para atualizar", payload

    bounds_only = client.put(
        "/api/profile/hr-zones", json={"bounds": LTHR_DEFAULTS}
    )
    assert bounds_only.status_code == 422
    assert bounds_only.json()["detail"] == "bounds exigem um método configurado"


def test_put_method_without_bounds_uses_defaults(session_client) -> None:
    """HRZ-08: method sem bounds -> config nova com os defaults do
    método, sem tocar nas métricas; zonas null sem as métricas exigidas
    (HRZ-11) e derivadas quando elas chegam (HRZ-10 — salvar → zonas
    mudam na hora)."""
    client, _user_id = session_client

    response = client.put("/api/profile/hr-zones", json={"method": "fcr"})
    assert response.status_code == 200
    body = response.json()
    assert body["config"] == {
        "method": "fcr", "bounds": FCR_DEFAULTS, "valid_from": TODAY_ISO,
    }
    assert body["metrics"] == {"fcmax": None, "fcrest": None, "fclthr": None}
    assert body["zones"] is None  # fcr exige fcrest e fcmax (HRZ-11)
    assert set(body["defaults"]) == {"lthr", "fcr", "fcmax"}  # shape do GET

    # métricas chegam -> zonas derivadas na hora (fcrest 50/fcmax 190)
    response = client.put(
        "/api/profile/hr-zones", json={"metrics": {"fcrest": 50, "fcmax": 190}}
    )
    assert response.status_code == 200
    assert response.json()["zones"] == [
        {"n": 1, "low": 120, "high": 134},
        {"n": 2, "low": 134, "high": 148},
        {"n": 3, "low": 148, "high": 162},
        {"n": 4, "low": 162, "high": 176},
        {"n": 5, "low": 176, "high": 190},
    ]


def test_put_custom_bounds_and_invalid_bounds_422(session_client) -> None:
    """HRZ-09: bounds custom criam config e recalculam as zonas
    (64/79/88/94/99 no lthr com fclthr 177); bounds inválidos -> 422
    com o PRIMEIRO ponto inválido, sem linha nova; mudar só um
    percentual mantém o método (edge: config nova herda o resto)."""
    client, user_id = session_client
    assert client.put(
        "/api/profile/hr-zones", json={"metrics": {"fclthr": 177}}
    ).status_code == 200

    custom = {"zones": [
        {"low": 64, "high": 79},
        {"low": 79, "high": 88},
        {"low": 88, "high": 94},
        {"low": 94, "high": 99},
        {"low": 99, "high": None},
    ]}
    response = client.put(
        "/api/profile/hr-zones", json={"method": "lthr", "bounds": custom}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["config"]["bounds"] == custom
    assert body["zones"] == [
        {"n": 1, "low": 113, "high": 140},
        {"n": 2, "low": 140, "high": 156},
        {"n": 3, "low": 156, "high": 166},
        {"n": 4, "low": 166, "high": 175},
        {"n": 5, "low": 175, "high": None},
    ]

    # cadeia quebrada na zona 2 -> 422 aponta a zona 2, não a 5
    broken = {"zones": [
        {"low": 64, "high": 79},
        {"low": 82, "high": 88},
        {"low": 88, "high": 94},
        {"low": 94, "high": 99},
        {"low": 99, "high": 105},  # segundo erro — não pode ser o motivo
    ]}
    response = client.put(
        "/api/profile/hr-zones", json={"method": "lthr", "bounds": broken}
    )
    assert response.status_code == 422
    assert "zona 2" in response.json()["detail"]
    assert "zona 5" not in response.json()["detail"]

    with SessionLocal() as db:
        assert db.query(HrZoneConfig).filter(HrZoneConfig.user_id == user_id).count() == 1

    # só o percentual muda (sem method) -> método fica o mesmo (edge)
    response = client.put(
        "/api/profile/hr-zones", json={"bounds": LTHR_DEFAULTS}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["config"]["method"] == "lthr"
    assert body["config"]["bounds"] == LTHR_DEFAULTS
    assert body["zones"][0] == {"n": 1, "low": 115, "high": 142}  # defaults de volta

    with SessionLocal() as db:
        assert db.query(HrZoneConfig).filter(HrZoneConfig.user_id == user_id).count() == 2


def test_put_metric_and_method_same_valid_from(session_client) -> None:
    """Edge do spec: PUT altera valor E método na mesma chamada -> ambas
    as linhas nascem com o mesmo valid_from (uma época coerente)."""
    client, user_id = session_client

    response = client.put(
        "/api/profile/hr-zones",
        json={"metrics": {"fclthr": 185}, "method": "lthr"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["metrics"]["fclthr"]["valid_from"] == TODAY_ISO
    assert body["config"]["valid_from"] == TODAY_ISO
    assert body["zones"][4] == {"n": 5, "low": 185, "high": None}  # lthr 185

    with SessionLocal() as db:
        metric = (
            db.query(UserHrMetric).filter(UserHrMetric.user_id == user_id).one()
        )
        config = (
            db.query(HrZoneConfig).filter(HrZoneConfig.user_id == user_id).one()
        )
        assert metric.valid_from == config.valid_from == TODAY


# ---------------------------------------------------------------
# GET /api/profile/hr-zones/history (HRZ-15)
# ---------------------------------------------------------------


def test_history_desc_by_valid_from_then_id(session_client) -> None:
    """HRZ-15: histórico de métricas e configs, mais recente primeiro
    (DESC por valid_from, tie-break id DESC), com data e fonte."""
    client, user_id = session_client
    with SessionLocal() as db:
        _seed_metric(db, user_id, "fclthr", 170, "garmin", date(2026, 10, 19))
        _seed_metric(db, user_id, "fclthr", 177, "garmin", date(2026, 10, 20))
        _seed_metric(db, user_id, "fclthr", 185, "manual", date(2026, 10, 20))
        _seed_config(db, user_id, "lthr", LTHR_DEFAULTS, date(2026, 10, 19))
        db.commit()

    response = client.get("/api/profile/hr-zones/history")
    assert response.status_code == 200
    body = response.json()

    # DESC: 185 (20/10, id maior) -> 177 (20/10) -> 170 (19/10)
    assert body["metrics"] == [
        {"kind": "fclthr", "value": 185, "source": "manual",
         "valid_from": "2026-10-20"},
        {"kind": "fclthr", "value": 177, "source": "garmin",
         "valid_from": "2026-10-20"},
        {"kind": "fclthr", "value": 170, "source": "garmin",
         "valid_from": "2026-10-19"},
    ]

    # config de hoje (via PUT) entra na frente da semeadra
    assert client.put(
        "/api/profile/hr-zones", json={"method": "fcr"}
    ).status_code == 200
    body = client.get("/api/profile/hr-zones/history").json()
    assert [c["method"] for c in body["configs"]] == ["fcr", "lthr"]
    assert body["configs"][0]["valid_from"] == TODAY_ISO
    assert body["configs"][0]["bounds"] == FCR_DEFAULTS
    assert body["configs"][1]["valid_from"] == "2026-10-19"


# ---------------------------------------------------------------
# Fronteira: sem sessão 401 + isolamento A×B (HRZ-16 padrão user-scope)
# ---------------------------------------------------------------


def test_hr_zones_endpoints_401_without_session(session_client) -> None:
    """Sem cookie -> 401 JSON nos 3 endpoints (padrão user-scope)."""
    client, _user_id = session_client
    client.cookies.delete("ritmo_session")

    for method, path, kwargs in (
        ("get", "/api/profile/hr-zones", {}),
        ("put", "/api/profile/hr-zones", {"json": {"metrics": {"fcmax": 190}}}),
        ("get", "/api/profile/hr-zones/history", {}),
    ):
        response = getattr(client, method)(path, **kwargs)
        assert response.status_code == 401, path
        assert response.json() == {"detail": "não autenticado"}


def test_hr_zones_isolated_between_users(session_client) -> None:
    """Isolamento A×B: métricas/config de Y não vazam para X (GET,
    history e PUT) e a escrita de X não toca as linhas de Y."""
    client, user_id = session_client
    with SessionLocal() as db:
        other, other_token = _new_user_with_token(db, "outra@example.com")
        _seed_metric(db, other.id, "fclthr", 171, "garmin", TODAY)
        _seed_config(db, other.id, "fcr", FCR_DEFAULTS, TODAY)
        db.commit()

    # X não vê nada de Y
    body = client.get("/api/profile/hr-zones").json()
    assert body["metrics"] == {"fcmax": None, "fcrest": None, "fclthr": None}
    assert body["config"] is None
    assert body["zones"] is None
    history = client.get("/api/profile/hr-zones/history").json()
    assert history == {"metrics": [], "configs": []}

    # escrita de X não toca Y
    assert client.put(
        "/api/profile/hr-zones", json={"metrics": {"fclthr": 185}}
    ).status_code == 200
    with SessionLocal() as db:
        assert db.query(UserHrMetric).filter(UserHrMetric.user_id == other.id).count() == 1
        assert db.query(HrZoneConfig).filter(HrZoneConfig.user_id == other.id).count() == 1

    # Y (cookie trocado) vê só as próprias linhas
    client.cookies.set("ritmo_session", other_token)
    body = client.get("/api/profile/hr-zones").json()
    assert body["metrics"]["fclthr"] == {
        "value": 171, "source": "garmin", "valid_from": TODAY_ISO,
    }
    assert body["config"]["method"] == "fcr"
    history = client.get("/api/profile/hr-zones/history").json()
    assert [m["value"] for m in history["metrics"]] == [171]
    assert [c["method"] for c in history["configs"]] == ["fcr"]
