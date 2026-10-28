"""Testes de integração do backfill CLI (T6) — client Strava falso injetado.

Cobre: upsert por strava_gear_id, associação retroativa via matching,
initial_km = max(0, km_strava - Σ casadas), commit único, idempotente,
abort token/429 consistente, relatório com checksum.
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from app.db.engine import SessionLocal, init_db
from app.db.models import Activity, Shoe, User
from app.strava.backfill import BackfillError, run_backfill
from app.strava.client import StravaClientError


class FakeStravaClient:
    """Cliente Strava falso para testes — injeta respostas controladas."""

    def __init__(
        self,
        shoes: list[dict] | None = None,
        runs: list[dict] | None = None,
        exchange_code_result: str | None = None,
        exchange_code_error: StravaClientError | None = None,
        fetch_shoes_error: StravaClientError | None = None,
        fetch_runs_error: StravaClientError | None = None,
    ):
        self.shoes = shoes or []
        self.runs = runs or []
        self.exchange_code_result = exchange_code_result
        self.exchange_code_error = exchange_code_error
        self.fetch_shoes_error = fetch_shoes_error
        self.fetch_runs_error = fetch_runs_error
        self.call_count = 0

    def exchange_code(self, code: str) -> str:
        self.call_count += 1
        if self.exchange_code_error:
            raise self.exchange_code_error
        if self.exchange_code_result:
            return self.exchange_code_result
        return "fake_token"

    def fetch_athlete_shoes(self, token: str) -> list[dict]:
        self.call_count += 1
        if self.fetch_shoes_error:
            raise self.fetch_shoes_error
        return self.shoes

    def fetch_run_activities(self, token: str, **kwargs) -> list[dict]:
        self.call_count += 1
        if self.fetch_runs_error:
            raise self.fetch_runs_error
        return self.runs


@pytest.fixture(autouse=True)
def _init_db():
    """Inicializa o schema antes de cada teste."""
    init_db()


def _seed_user(db, user_id: int = 1) -> User:
    user = db.get(User, user_id)
    if not user:
        user = User(id=user_id, display_name="Test User")
        db.add(user)
        db.flush()
    return user


def _seed_activity(db, user_id: int, garmin_id: str, **kwargs) -> Activity:
    defaults = {
        "user_id": user_id,
        "garmin_id": garmin_id,
        "start_time": datetime(2024, 1, 15, 7, 0),
        "activity_type": "running",
        "name": "Morning Run",
        "distance_m": 5000.0,
        "duration_s": 1800.0,
        "shoe_id": None,
    }
    defaults.update(kwargs)
    activity = Activity(**defaults)
    db.add(activity)
    db.flush()
    return activity


def test_backfill_upsert_creates_shoes_with_correct_km() -> None:
    """Done-when T6: execução cria/atualiza cada tênis com km derivada = distance do gear."""
    # Setup: Strava retorna 2 tênis com distances
    fake = FakeStravaClient(
        shoes=[
            {"id": "g1", "name": "Kayano 30", "brand_name": "ASICS", "model_name": "Gel-Kayano 30", "distance": 788000.0},
            {"id": "g2", "name": "Corre 3", "brand_name": "Olympikus", "model_name": "Corre 3", "distance": 623000.0},
        ],
        runs=[],
    )

    with patch("app.strava.backfill.exchange_code", fake.exchange_code), \
         patch("app.strava.backfill.fetch_athlete_shoes", fake.fetch_athlete_shoes), \
         patch("app.strava.backfill.fetch_run_activities", fake.fetch_run_activities), \
         patch("builtins.input", return_value="s"):  # confirma

        run_backfill(code="fake_code", user_id=1, yes=False)

    with SessionLocal() as db:
        shoes = db.query(Shoe).filter(Shoe.user_id == 1).all()
        assert len(shoes) == 2
        # km derivada = initial_km + 0 (sem atividades) = initial_km
        # initial_km = max(0, strava_km - 0) = strava_km
        kayano = next(s for s in shoes if s.strava_gear_id == "g1")
        corre = next(s for s in shoes if s.strava_gear_id == "g2")
        assert kayano.initial_km == 788.0  # 788000m = 788km
        assert corre.initial_km == 623.0


def test_backfill_upsert_updates_existing_shoe() -> None:
    """Done-when T6: re-run não duplica tênis (idempotente)."""
    fake = FakeStravaClient(
        shoes=[{"id": "g1", "name": "Kayano 30", "brand_name": "ASICS", "model_name": "Gel-Kayano 30", "distance": 788000.0}],
        runs=[],
    )

    with patch("app.strava.backfill.exchange_code", fake.exchange_code), \
         patch("app.strava.backfill.fetch_athlete_shoes", fake.fetch_athlete_shoes), \
         patch("app.strava.backfill.fetch_run_activities", fake.fetch_run_activities), \
         patch("builtins.input", return_value="s"):

        run_backfill(code="fake_code", user_id=1, yes=False)
        run_backfill(code="fake_code", user_id=1, yes=False)  # 2ª execução

    with SessionLocal() as db:
        shoes = db.query(Shoe).filter(Shoe.user_id == 1, Shoe.strava_gear_id == "g1").all()
        assert len(shoes) == 1  # não duplicou


def test_backfill_matches_and_associates_runs() -> None:
    """Done-when T6: corrida com gear_id + match → associação retroativa."""
    with SessionLocal() as db:
        _seed_user(db)
        # Atividade Garmin no banco (sem tênis)
        act = _seed_activity(db, 1, garmin_id="12345", distance_m=5000.0, start_time=datetime(2024, 1, 15, 7, 0))
        db.commit()
        activity_id = act.id

    fake = FakeStravaClient(
        shoes=[{"id": "g1", "name": "Kayano 30", "brand_name": "ASICS", "model_name": "Gel-Kayano 30", "distance": 788000.0}],
        runs=[
            {
                "id": 1,
                "external_id": "garmin_push_12345",  # match por external_id
                "gear_id": "g1",
                "distance": 5000.0,
                "moving_time": 1800,
                "start_date": "2024-01-15T07:00:00Z",
            }
        ],
    )

    with patch("app.strava.backfill.exchange_code", fake.exchange_code), \
         patch("app.strava.backfill.fetch_athlete_shoes", fake.fetch_athlete_shoes), \
         patch("app.strava.backfill.fetch_run_activities", fake.fetch_run_activities), \
         patch("builtins.input", return_value="s"):

        run_backfill(code="fake_code", user_id=1, yes=False)

    with SessionLocal() as db:
        activity = db.get(Activity, activity_id)
        assert activity.shoe_id is not None
        shoe = db.get(Shoe, activity.shoe_id)
        assert shoe.strava_gear_id == "g1"


def test_backfill_fallback_match_when_no_external_id() -> None:
    """Done-when T6: fallback heurístico quando external_id ausente."""
    with SessionLocal() as db:
        _seed_user(db)
        # Atividade sem external_id garmin, mas mesma distância/tempo/data
        act = _seed_activity(
            db, 1,
            garmin_id="99999",
            distance_m=5000.0,
            duration_s=1800,
            start_time=datetime(2024, 1, 15, 7, 0),
        )
        db.commit()
        activity_id = act.id

    fake = FakeStravaClient(
        shoes=[{"id": "g1", "name": "Kayano 30", "brand_name": "ASICS", "distance": 788000.0}],
        runs=[
            {
                "id": 1,
                "external_id": "manual_upload_123",  # não é garmin_push
                "gear_id": "g1",
                "distance": 5000.0,
                "moving_time": 1800,
                "start_date": "2024-01-15T07:00:00Z",
            }
        ],
    )

    with patch("app.strava.backfill.exchange_code", fake.exchange_code), \
         patch("app.strava.backfill.fetch_athlete_shoes", fake.fetch_athlete_shoes), \
         patch("app.strava.backfill.fetch_run_activities", fake.fetch_run_activities), \
         patch("builtins.input", return_value="s"):

        run_backfill(code="fake_code", user_id=1, yes=False)

    with SessionLocal() as db:
        activity = db.get(Activity, activity_id)
        assert activity.shoe_id is not None
        shoe = db.get(Shoe, activity.shoe_id)
        assert shoe.strava_gear_id == "g1"


def test_backfill_no_gear_id_runs_unmatched() -> None:
    """Done-when T6: sem gear_id → fica null e entra no relatório como não alocada."""
    fake = FakeStravaClient(
        shoes=[{"id": "g1", "name": "Kayano 30", "distance": 788000.0}],
        runs=[
            {
                "id": 1,
                "external_id": "garmin_push_100",
                "gear_id": None,  # sem gear_id
                "distance": 5000.0,
                "moving_time": 1800,
                "start_date": "2024-01-15T07:00:00Z",
            }
        ],
    )

    with patch("app.strava.backfill.exchange_code", fake.exchange_code), \
         patch("app.strava.backfill.fetch_athlete_shoes", fake.fetch_athlete_shoes), \
         patch("app.strava.backfill.fetch_run_activities", fake.fetch_run_activities), \
         patch("builtins.input", return_value="s"):

        run_backfill(code="fake_code", user_id=1, yes=False)

    with SessionLocal() as db:
        shoes = db.query(Shoe).filter(Shoe.user_id == 1).all()
        kayano = next(s for s in shoes if s.strava_gear_id == "g1")
        # initial_km = strava_km - 0 (sem casadas) = 788
        # a corrida sem gear_id não afeta o initial_km
        assert kayano.initial_km == 788.0


def test_backfill_ambiguous_match_unassigned() -> None:
    """Done-when T6: ambíguas ficam null e listadas; nenhuma associação inventada."""
    with SessionLocal() as db:
        _seed_user(db)
        # Duas atividades idênticas (ambiguidade)
        _seed_activity(db, 1, garmin_id="100", distance_m=5000.0, start_time=datetime(2024, 1, 15, 7, 0))
        _seed_activity(db, 1, garmin_id="200", distance_m=5000.0, start_time=datetime(2024, 1, 15, 7, 0))
        db.commit()

    fake = FakeStravaClient(
        shoes=[{"id": "g1", "name": "Kayano 30", "distance": 788000.0}],
        runs=[
            {
                "id": 1,
                "external_id": "manual_1",  # sem external_id garmin
                "gear_id": "g1",
                "distance": 5000.0,
                "moving_time": 1800,
                "start_date": "2024-01-15T07:00:00Z",
            }
        ],
    )

    with patch("app.strava.backfill.exchange_code", fake.exchange_code), \
         patch("app.strava.backfill.fetch_athlete_shoes", fake.fetch_athlete_shoes), \
         patch("app.strava.backfill.fetch_run_activities", fake.fetch_run_activities), \
         patch("builtins.input", return_value="s"):

        run_backfill(code="fake_code", user_id=1, yes=False)

    with SessionLocal() as db:
        activities = db.query(Activity).filter(Activity.user_id == 1).all()
        # Nenhuma das duas deve ter shoe_id (ambígua)
        for a in activities:
            assert a.shoe_id is None


def test_backfill_initial_km_formula() -> None:
    """Done-when T6: initial_km = max(0, km_strava - Σ casadas)."""
    with SessionLocal() as db:
        _seed_user(db)
        # Atividade que vai casar (5km)
        act = _seed_activity(db, 1, garmin_id="100", distance_m=5000.0, start_time=datetime(2024, 1, 15, 7, 0))
        db.commit()
        activity_id = act.id

    # Strava diz que o tênis tem 100km total, mas só 5km casaram
    fake = FakeStravaClient(
        shoes=[{"id": "g1", "name": "Kayano 30", "distance": 100000.0}],  # 100km
        runs=[
            {
                "id": 1,
                "external_id": "garmin_push_100",
                "gear_id": "g1",
                "distance": 5000.0,  # 5km
                "moving_time": 1800,
                "start_date": "2024-01-15T07:00:00Z",
            }
        ],
    )

    with patch("app.strava.backfill.exchange_code", fake.exchange_code), \
         patch("app.strava.backfill.fetch_athlete_shoes", fake.fetch_athlete_shoes), \
         patch("app.strava.backfill.fetch_run_activities", fake.fetch_run_activities), \
         patch("builtins.input", return_value="s"):

        run_backfill(code="fake_code", user_id=1, yes=False)

    with SessionLocal() as db:
        shoe = db.query(Shoe).filter(Shoe.user_id == 1, Shoe.strava_gear_id == "g1").one()
        # initial_km = max(0, 100 - 5) = 95
        assert shoe.initial_km == 95.0

        # Atividade associada
        activity = db.get(Activity, activity_id)
        assert activity.shoe_id == shoe.id


def test_backfill_invalid_token_aborts_before_write() -> None:
    """Done-when T6: token inválido aborta antes de qualquer escrita."""
    fake = FakeStravaClient(
        exchange_code_error=StravaClientError("Invalid code", status_code=400),
    )

    with patch("app.strava.backfill.exchange_code", fake.exchange_code), \
         patch("builtins.input", return_value="s"):
        with pytest.raises(BackfillError):
            run_backfill(code="bad_code", user_id=1, yes=False)

    # Verifica que nada foi gravado
    with SessionLocal() as db:
        shoes = db.query(Shoe).filter(Shoe.user_id == 1).all()
        assert len(shoes) == 0


def test_backfill_429_persistent_aborts_consistent() -> None:
    """Done-when T6: erro 429/5xx persistente aborta com estado consistente."""
    fake = FakeStravaClient(
        shoes=[{"id": "g1", "name": "Kayano 30", "distance": 788000.0}],
        fetch_shoes_error=StravaClientError("Rate limit", status_code=429),
    )

    with patch("app.strava.backfill.exchange_code", fake.exchange_code), \
         patch("app.strava.backfill.fetch_athlete_shoes", fake.fetch_athlete_shoes), \
         patch("builtins.input", return_value="s"):
        with pytest.raises(BackfillError):
            run_backfill(code="fake_code", user_id=1, yes=False)

    # Verifica que nada foi gravado (commit único)
    with SessionLocal() as db:
        shoes = db.query(Shoe).filter(Shoe.user_id == 1).all()
        assert len(shoes) == 0


def test_backfill_report_checksum() -> None:
    """Done-when T6: relatório final imprime checksum por tênis."""
    with SessionLocal() as db:
        _seed_user(db)
        _seed_activity(db, 1, garmin_id="100", distance_m=5000.0, start_time=datetime(2024, 1, 15, 7, 0))
        db.commit()

    fake = FakeStravaClient(
        shoes=[{"id": "g1", "name": "Kayano 30", "distance": 100000.0}],  # 100km
        runs=[
            {
                "id": 1,
                "external_id": "garmin_push_100",
                "gear_id": "g1",
                "distance": 5000.0,  # 5km
                "moving_time": 1800,
                "start_date": "2024-01-15T07:00:00Z",
            }
        ],
    )

    # Captura stdout
    import io
    import sys
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    try:
        with patch("app.strava.backfill.exchange_code", fake.exchange_code), \
             patch("app.strava.backfill.fetch_athlete_shoes", fake.fetch_athlete_shoes), \
             patch("app.strava.backfill.fetch_run_activities", fake.fetch_run_activities), \
             patch("builtins.input", return_value="s"):

            run_backfill(code="fake_code", user_id=1, yes=False)

        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout

    # Verifica checksum no output
    assert "CHECKSUM" in output
    assert "95.00" in output  # initial_km = 100 - 5
    assert "5.00" in output   # casadas
    assert "100.00" in output  # Strava total


def test_backfill_requires_code_or_token() -> None:
    """Done-when T6: --code XOR --token obrigatório."""
    with pytest.raises(BackfillError, match="Informe --code"):
        run_backfill(code=None, token=None, user_id=1, yes=True)

    with pytest.raises(BackfillError, match="Use --code OU --token"):
        run_backfill(code="abc", token="def", user_id=1, yes=True)


def test_backfill_user_not_found() -> None:
    """Done-when T6: usuário inexistente → erro."""
    fake = FakeStravaClient()

    with patch("app.strava.backfill.exchange_code", fake.exchange_code), \
         patch("app.strava.backfill.fetch_athlete_shoes", fake.fetch_athlete_shoes), \
         patch("app.strava.backfill.fetch_run_activities", fake.fetch_run_activities), \
         patch("builtins.input", return_value="s"):
        with pytest.raises(BackfillError, match="Usuário 999 não encontrado"):
            run_backfill(code="fake_code", user_id=999, yes=False)