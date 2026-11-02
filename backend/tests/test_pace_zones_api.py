"""API de zonas de ritmo (T5, feature pace-zones) — HTTP no Postgres real.

Rotas em escopo (matriz): happy path (200 + shape), 401 sem sessão,
500 sem configuração, isolamento A×B — com `session_client` (sessão
real por usuário; o conftest semeia o usuário, os testes o user_id
devolvido). Valores afirmados são literais do spec (vdot_zones.json).
"""

from app.db.engine import SessionLocal
from app.db.models import VdotZoneConfig, User


def test_get_pace_zones_full_shape(session_client) -> None:
    """Happy path: com sessão, o shape completo — vdot, source, test_date,
    distancia_metros, tempo_segundos, 5 zonas com pace/description/ms,
    equivalencias de prova."""
    client, user_id = session_client

    # Seed VdotZoneConfig for this test user (init_db seeds only DEFAULT_USER_ID=1)
    from app.db.engine import SessionLocal
    from app.db.models import VdotZoneConfig
    from datetime import date
    with SessionLocal() as db:
        db.add(VdotZoneConfig(
            user_id=user_id,
            vdot=50.2,
            source="10K em 41:15",
            test_date=date(2026, 10, 3),
            distance_m=10012.0,
            time_s=2475.0,
            zones={
                "easy": {"pace_range": "5:51/km-4:53/km", "ms_min": 2.851, "ms_max": 3.418, "description": "Recuperação, base aeróbica, aquecimento/desaquecimento"},
                "marathon": {"pace": "4:30/km", "ms": 3.701, "description": "Ritmo de maratona, longões"},
                "threshold": {"pace_range": "4:14/km-4:27/km", "ms_min": 3.749, "ms_max": 3.931, "description": "Limiar de lactato, tempo runs"},
                "interval": {"pace_range": "3:59/km-3:49/km", "ms_min": 4.183, "ms_max": 4.36, "description": "VO2max, esforços de 2-4 min"},
                "repetition": {"pace": "3:40/km", "ms": 4.536, "description": "Repetições curtas, 800m-1km"},
            },
            equivalencias={
                "5K": "3:58/km",
                "10K": "4:07/km",
                "Meia Maratona": "4:19/km",
                "Maratona": "4:30/km",
            },
            valid_from=date(2026, 10, 3),
        ))
        db.commit()

    response = client.get("/api/profile/pace-zones")
    assert response.status_code == 200
    body = response.json()

    # Campos raiz
    assert body["vdot"] == 50.2
    assert body["source"] == "10K em 41:15"
    assert body["test_date"] == "2026-10-03"
    assert body["distancia_metros"] == 10012.0
    assert body["tempo_segundos"] == 2475.0

    # 5 zonas
    zones = body["zones"]
    assert set(zones.keys()) == {"easy", "marathon", "threshold", "interval", "repetition"}

    # Easy: pace_range + ms_min + ms_max
    easy = zones["easy"]
    assert easy["key"] == "easy"
    assert easy["pace_range"] == "5:51/km-4:53/km"
    assert easy["ms_min"] == 2.851
    assert easy["ms_max"] == 3.418
    assert easy["description"] == "Recuperação, base aeróbica, aquecimento/desaquecimento"

    # Marathon: pace + ms
    marathon = zones["marathon"]
    assert marathon["key"] == "marathon"
    assert marathon["pace"] == "4:30/km"
    assert marathon["ms"] == 3.701
    assert marathon["description"] == "Ritmo de maratona, longões"

    # Threshold: pace_range + ms_min + ms_max
    threshold = zones["threshold"]
    assert threshold["key"] == "threshold"
    assert threshold["pace_range"] == "4:14/km-4:27/km"
    assert threshold["ms_min"] == 3.749
    assert threshold["ms_max"] == 3.931
    assert threshold["description"] == "Limiar de lactato, tempo runs"

    # Interval: pace_range + ms_min + ms_max
    interval = zones["interval"]
    assert interval["key"] == "interval"
    assert interval["pace_range"] == "3:59/km-3:49/km"
    assert interval["ms_min"] == 4.183
    assert interval["ms_max"] == 4.36
    assert interval["description"] == "VO2max, esforços de 2-4 min"

    # Repetition: pace + ms
    repetition = zones["repetition"]
    assert repetition["key"] == "repetition"
    assert repetition["pace"] == "3:40/km"
    assert repetition["ms"] == 4.536
    assert repetition["description"] == "Repetições curtas, 800m-1km"

    # Equivalências
    equiv = body["equivalencias"]
    assert equiv["5K"] == "3:58/km"
    assert equiv["10K"] == "4:07/km"
    assert equiv["Meia Maratona"] == "4:19/km"
    assert equiv["Maratona"] == "4:30/km"


def test_get_pace_zones_401_without_session() -> None:
    """Sem sessão → 401 (padrão do include no main)."""
    from app.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.get("/api/profile/pace-zones")
    assert response.status_code == 401


def test_get_pace_zones_500_without_config(session_client) -> None:
    """Usuário sem linha em vdot_zone_configs → 500 'zonas VDOT não configuradas'."""
    client, user_id = session_client

    # Apagar a linha seedada pelo init_db para este usuário
    with SessionLocal() as db:
        db.query(VdotZoneConfig).filter(VdotZoneConfig.user_id == user_id).delete()
        db.commit()

    response = client.get("/api/profile/pace-zones")
    assert response.status_code == 500
    assert response.json()["detail"] == "zonas VDOT não configuradas"


def test_get_pace_zones_isolated_between_users(no_vdot_zones) -> None:
    """Isolamento A×B: usuário A não vê dados do usuário B (seed user 1)."""
    client, user_id = no_vdot_zones

    # User A (novo) não tem config
    response = client.get("/api/profile/pace-zones")
    assert response.status_code == 500
    assert response.json()["detail"] == "zonas VDOT não configuradas"


# =============================================================================
# POST /api/profile/pace-zones/recalibrate
# =============================================================================


def test_recalibrate_pace_zones_creates_new_config(session_client) -> None:
    """POST com distância e tempo válidos cria nova config e retorna shape completo."""
    client, user_id = session_client

    # Limpar config existente
    with SessionLocal() as db:
        db.query(VdotZoneConfig).filter(VdotZoneConfig.user_id == user_id).delete()
        db.commit()

    # 10K em 40:12 → VDOT 51.6 pela forma fechada de app/vdot/daniels.py
    # (fonte de verdade do produto — a mesma que gerou a calibração 50.2;
    # diverge ~0.2–1.3 das tabelas impressas de Daniels, registrado no audit)
    response = client.post(
        "/api/profile/pace-zones/recalibrate",
        json={"distance_km": 10.0, "time_str": "00:40:12"},
    )
    assert response.status_code == 200
    body = response.json()

    # Campos raiz
    assert body["vdot"] == 51.6  # arredondado para 1 casa
    assert "10.000km" in body["source"]
    assert "00:40:12" in body["source"]
    assert body["distancia_metros"] == 10000.0
    assert body["tempo_segundos"] == 2412.0

    # 5 zonas presentes
    zones = body["zones"]
    assert set(zones.keys()) == {"easy", "marathon", "threshold", "interval", "repetition"}

    # Easy tem pace_range
    assert "pace_range" in zones["easy"]
    assert zones["easy"]["key"] == "easy"

    # Marathon tem pace (single)
    assert "pace" in zones["marathon"]
    assert zones["marathon"]["key"] == "marathon"

    # Equivalências
    equiv = body["equivalencias"]
    assert set(equiv.keys()) == {"5K", "10K", "Meia Maratona", "Maratona"}

    # Verificar que salvou no banco
    with SessionLocal() as db:
        config = db.query(VdotZoneConfig).filter(VdotZoneConfig.user_id == user_id).first()
        assert config is not None
        assert config.vdot == 51.6
        assert config.distance_m == 10000.0
        assert config.time_s == 2412.0


def test_recalibrate_pace_zones_updates_existing_config(session_client) -> None:
    """POST em usuário com config existente faz upsert (atualiza)."""
    client, user_id = session_client

    # Primeiro POST
    response1 = client.post(
        "/api/profile/pace-zones/recalibrate",
        json={"distance_km": 10.0, "time_str": "00:40:12"},
    )
    assert response1.status_code == 200
    assert response1.json()["vdot"] == 51.6

    # Segundo POST com tempo diferente
    response2 = client.post(
        "/api/profile/pace-zones/recalibrate",
        json={"distance_km": 10.0, "time_str": "00:42:00"},
    )
    assert response2.status_code == 200
    # 10K em 42:00 → VDOT 49.1 pela forma fechada
    assert response2.json()["vdot"] == 49.1

    # Só deve ter 1 linha no banco
    with SessionLocal() as db:
        count = db.query(VdotZoneConfig).filter(VdotZoneConfig.user_id == user_id).count()
        assert count == 1
        config = db.query(VdotZoneConfig).filter(VdotZoneConfig.user_id == user_id).first()
        assert config.vdot == 49.1


def test_recalibrate_pace_zones_422_invalid_distance(session_client) -> None:
    """distance_km <= 0 → 422."""
    client, user_id = session_client

    response = client.post(
        "/api/profile/pace-zones/recalibrate",
        json={"distance_km": 0, "time_str": "00:40:12"},
    )
    assert response.status_code == 422
    # O RecalibrateIn valida gt=0 no schema — detail é a lista padrão do FastAPI
    detail = response.json()["detail"]
    assert any(item.get("loc", [None, None])[1] == "distance_km" for item in detail)


def test_recalibrate_pace_zones_422_invalid_time_format(session_client) -> None:
    """time_str formato inválido → 422."""
    client, user_id = session_client

    response = client.post(
        "/api/profile/pace-zones/recalibrate",
        json={"distance_km": 10.0, "time_str": "invalid"},
    )
    assert response.status_code == 422
    assert "time_str" in response.json()["detail"]


def test_recalibrate_pace_zones_422_zero_time(session_client) -> None:
    """time_str = 00:00:00 → 422."""
    client, user_id = session_client

    response = client.post(
        "/api/profile/pace-zones/recalibrate",
        json={"distance_km": 10.0, "time_str": "00:00:00"},
    )
    assert response.status_code == 422
    assert "time_str" in response.json()["detail"]


def test_recalibrate_pace_zones_422_future_test_date(session_client) -> None:
    """test_date no futuro → 422."""
    client, user_id = session_client
    from datetime import date, timedelta
    future = (date.today() + timedelta(days=1)).isoformat()

    response = client.post(
        "/api/profile/pace-zones/recalibrate",
        json={"distance_km": 10.0, "time_str": "00:40:12", "test_date": future},
    )
    assert response.status_code == 422
    assert "test_date" in response.json()["detail"]


def test_recalibrate_pace_zones_422_invalid_test_date_format(session_client) -> None:
    """test_date formato inválido → 422."""
    client, user_id = session_client

    response = client.post(
        "/api/profile/pace-zones/recalibrate",
        json={"distance_km": 10.0, "time_str": "00:40:12", "test_date": "invalid"},
    )
    assert response.status_code == 422
    assert "test_date" in response.json()["detail"]


def test_recalibrate_pace_zones_mm_ss_format(session_client) -> None:
    """time_str no formato MM:SS funciona (ex: 40:12)."""
    client, user_id = session_client

    with SessionLocal() as db:
        db.query(VdotZoneConfig).filter(VdotZoneConfig.user_id == user_id).delete()
        db.commit()

    response = client.post(
        "/api/profile/pace-zones/recalibrate",
        json={"distance_km": 10.0, "time_str": "40:12"},
    )
    assert response.status_code == 200
    assert response.json()["vdot"] == 51.6


def test_recalibrate_pace_zones_5k_distance(session_client) -> None:
    """Teste com 5K (distância padrão)."""
    client, user_id = session_client

    with SessionLocal() as db:
        db.query(VdotZoneConfig).filter(VdotZoneConfig.user_id == user_id).delete()
        db.commit()

    # 5K em 19:30 → VDOT 51.3 pela forma fechada (tabelas impressas: 50.0 —
    # divergência conhecida da fórmula, audit-erros.md HER-05)
    response = client.post(
        "/api/profile/pace-zones/recalibrate",
        json={"distance_km": 5.0, "time_str": "19:30"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["vdot"] == 51.3
    assert body["distancia_metros"] == 5000.0
    assert body["tempo_segundos"] == 1170.0