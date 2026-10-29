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


def test_get_pace_zones_isolated_between_users(session_client) -> None:
    """Isolamento A×B: usuário A não vê dados do usuário B (seed user 1)."""
    client, user_id = session_client

    # User A (novo) não tem config
    response = client.get("/api/profile/pace-zones")
    assert response.status_code == 500
    assert response.json()["detail"] == "zonas VDOT não configuradas"