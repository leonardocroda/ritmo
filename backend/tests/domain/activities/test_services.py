"""Testes dos serviços puros do domínio Activities."""

import pytest

from app.domain.activities.domain.value_objects import (
    Pace,
    HeartRate,
    Cadence,
    ZoneKey,
    ZoneConfigVO,
)
from app.domain.activities.domain.entities import (
    Activity,
    Split,
    RunningDynamics,
)
from app.domain.activities.domain.services import (
    ConsistencyCalculator,
    ConsistencyMetrics,
    split_halves,
    _half_pace,
    _weighted_mean,
    _decoupling,
    infer_type,
    derive_structure,
    classify_splits,
    ClassifiedSplit,
    WORK_ZONES,
    RECOVERY_ZONES,
    LONG_RUN_MIN_M,
    BLOCK_MIN_LAPS,
    BLOCK_MIN_METERS,
    PROGRESSIVE_MAX_RATIO,
)


def create_basic_activity(
    distance_m: float = 10000.0,
    duration_s: float = 3000.0,
    splits: list[Split] | None = None,
) -> Activity:
    """Cria atividade básica para testes."""
    return Activity(
        id=1,
        user_id=1,
        start_time=__import__("datetime").datetime.now(),
        activity_type="running",
        name="Test Run",
        distance_m=distance_m,
        duration_s=duration_s,
        avg_hr=HeartRate(150),
        max_hr=HeartRate(165),
        avg_cadence=Cadence(180),
        elevation_gain_m=50.0,
        aerobic_te=100.0,
        anaerobic_te=10.0,
        training_load=50.0,
        inferred_type="facil",
        structure=None,
        splits=tuple(splits) if splits else (),
        evaluated=False,
    )


def create_splits(
    count: int,
    pace_s_km: float = 300.0,
    distance_each_m: float = 1000.0,
    hr: int = 150,
    cadence: int = 180,
    zone: str = "threshold",
    intensity: str = "ACTIVE",
) -> list[Split]:
    """Cria lista de splits uniformes para testes.

    duration_s é calculado automaticamente: pace_s_km * (distance_each_m / 1000)
    """
    pace = Pace.from_seconds_per_km(pace_s_km)
    duration_each_s = pace_s_km * (distance_each_m / 1000.0)
    splits = []
    for i in range(count):
        splits.append(
            Split(
                idx=i + 1,
                distance_m=distance_each_m,
                duration_s=duration_each_s,
                pace=pace,
                avg_hr=HeartRate(hr),
                avg_cadence=Cadence(cadence),
                avg_temperature=20.0,
                elevation_m=0.0,
                intensity_type=intensity,
                zone=ZoneKey(zone),
                km_label=f"{i + 1},0",
            )
        )
    return splits


class TestSplitHalves:
    def test_even_split(self):
        """Divisão igual com distância par."""
        splits = create_splits(4, distance_each_m=2000.0)  # 8km total
        first, second = split_halves(splits)
        assert len(first) == 2
        assert len(second) == 2
        assert sum(s.distance_m for s in first) == 4000.0
        assert sum(s.distance_m for s in second) == 4000.0

    def test_odd_split_crosses_middle(self):
        """Volta que atravessa o meio fica na primeira metade."""
        splits = create_splits(3, distance_each_m=3000.0)  # 9km total
        first, second = split_halves(splits)
        # 4.5km target, primeira volta 3km, segunda 3km -> atinge 6km >= 4.5km
        assert len(first) == 2  # primeira e segunda volta
        assert len(second) == 1  # terceira volta
        assert sum(s.distance_m for s in first) == 6000.0

    def test_single_split(self):
        splits = create_splits(1, distance_each_m=5000.0)
        first, second = split_halves(splits)
        assert len(first) == 1
        assert len(second) == 0


class TestHalfPace:
    def test_valid_pace(self):
        splits = create_splits(4)
        pace = _half_pace(splits)
        assert pace == 300.0  # pace uniforme

    def test_ignores_invalid_splits(self):
        splits = create_splits(3)
        # Torna uma split inválida
        splits[1] = Split(
            idx=2,
            distance_m=None,
            duration_s=None,
            pace=None,
            avg_hr=None,
            avg_cadence=None,
            avg_temperature=None,
            elevation_m=None,
            intensity_type=None,
            zone=None,
            km_label="2,0",
        )
        pace = _half_pace(splits)
        assert pace == 300.0  # apenas as 2 válidas

    def test_no_valid_pace(self):
        splits = [
            Split(idx=1, distance_m=None, duration_s=None, pace=None,
                  avg_hr=None, avg_cadence=None, avg_temperature=None,
                  elevation_m=None, intensity_type=None, zone=None, km_label="1,0"),
        ]
        pace = _half_pace(splits)
        assert pace is None


class TestWeightedMean:
    def test_weighted_by_duration(self):
        splits = create_splits(2, hr=140, cadence=170, pace_s_km=200.0)
        splits.append(Split(
            idx=3, distance_m=1000, duration_s=400.0,
            pace=Pace.from_seconds_per_km(400),
            avg_hr=HeartRate(160), avg_cadence=Cadence(190),
            avg_temperature=None, elevation_m=None,
            intensity_type="ACTIVE", zone=ZoneKey("threshold"), km_label="3,0"
        ))
        # Média ponderada: (140*200 + 140*200 + 160*400) / (200+200+400) = 150
        hr_mean = _weighted_mean(splits, "avg_hr")
        assert hr_mean is not None
        assert abs(hr_mean - 150.0) < 1.0

    def test_none_when_no_data(self):
        splits = create_splits(2, hr=None)
        # Remove HR
        splits = [
            Split(idx=i+1, distance_m=1000, duration_s=300,
                  pace=Pace.from_seconds_per_km(300),
                  avg_hr=None, avg_cadence=Cadence(180),
                  avg_temperature=None, elevation_m=None,
                  intensity_type="ACTIVE", zone=ZoneKey("threshold"), km_label=f"{i+1},0")
            for i in range(2)
        ]
        hr_mean = _weighted_mean(splits, "avg_hr")
        assert hr_mean is None


class TestDecoupling:
    def test_decoupling_when_pace_slows_and_hr_rises(self):
        # Pace 300->330 (slower), HR 150->160 (higher)
        # ratio_first = 150/300 = 0.5, ratio_second = 160/330 = 0.485
        # (0.485 - 0.5) / 0.5 = -3%
        result = _decoupling(300.0, 330.0, 150.0, 160.0)
        assert result is not None
        assert result < 0  # Fórmula HR/pace diminui quando pace sobe mais que HR

    def test_decoupling_when_pace_improves_and_hr_drops(self):
        # Pace 330->300 (faster), HR 160->150 (lower)
        # ratio_first = 160/330 = 0.485, ratio_second = 150/300 = 0.5
        # (0.5 - 0.485) / 0.485 = +3.1%
        result = _decoupling(330.0, 300.0, 160.0, 150.0)
        assert result is not None
        assert result > 0

    def test_none_when_missing_data(self):
        assert _decoupling(None, 300.0, 150.0, 160.0) is None
        assert _decoupling(300.0, 330.0, None, 160.0) is None
        assert _decoupling(300.0, 330.0, 150.0, None) is None


class TestConsistencyCalculator:
    def setup_method(self):
        self.calc = ConsistencyCalculator()

    def test_below_gate_distance(self):
        """None para distância < 8km."""
        activity = create_basic_activity(distance_m=5000.0, splits=create_splits(5))
        result = self.calc.calculate(activity, activity.splits)
        assert result is None

    def test_below_gate_splits(self):
        """None para < 4 voltas."""
        activity = create_basic_activity(distance_m=10000.0, splits=create_splits(3))
        result = self.calc.calculate(activity, activity.splits)
        assert result is None

    def test_at_gate(self):
        """Retorna métricas exatamente no gate (8km, 4 voltas)."""
        activity = create_basic_activity(distance_m=8000.0, splits=create_splits(4, distance_each_m=2000.0))
        result = self.calc.calculate(activity, activity.splits)
        assert result is not None
        assert isinstance(result, ConsistencyMetrics)

    def test_pace_balance(self):
        """Testa cálculo de equilíbrio de pace."""
        # Primeira metade pace 300, segunda 310 -> delta +10s, +3.3%
        splits = create_splits(4, distance_each_m=2500.0)
        # Modifica pace da segunda metade
        pace_slow = Pace.from_seconds_per_km(310)
        splits[2] = Split(idx=3, distance_m=2500, duration_s=775, pace=pace_slow,
                          avg_hr=HeartRate(155), avg_cadence=Cadence(180),
                          avg_temperature=None, elevation_m=None,
                          intensity_type="ACTIVE", zone=ZoneKey("threshold"), km_label="3,0")
        splits[3] = Split(idx=4, distance_m=2500, duration_s=775, pace=pace_slow,
                          avg_hr=HeartRate(155), avg_cadence=Cadence(180),
                          avg_temperature=None, elevation_m=None,
                          intensity_type="ACTIVE", zone=ZoneKey("threshold"), km_label="4,0")

        activity = create_basic_activity(distance_m=10000.0, splits=splits)
        result = self.calc.calculate(activity, activity.splits)

        assert result is not None
        assert result.first_half_pace_s == 300.0
        assert result.second_half_pace_s == 310.0
        assert result.balance_delta_s == 10.0
        assert abs(result.balance_delta_pct - 3.3) < 0.1

    def test_hr_drift(self):
        """Testa drift cardíaco."""
        splits = create_splits(4, distance_each_m=2500.0, hr=150)
        # Segunda metade HR maior
        for i in [2, 3]:
            splits[i] = Split(
                idx=i+1, distance_m=2500, duration_s=750,
                pace=Pace.from_seconds_per_km(300),
                avg_hr=HeartRate(160), avg_cadence=Cadence(180),
                avg_temperature=None, elevation_m=None,
                intensity_type="ACTIVE", zone=ZoneKey("threshold"), km_label=f"{i+1},0"
            )

        activity = create_basic_activity(distance_m=10000.0, splits=splits)
        result = self.calc.calculate(activity, activity.splits)

        assert result is not None
        assert result.first_half_hr == 150.0
        assert result.second_half_hr == 160.0
        assert result.hr_drift_bpm == 10.0

    def test_cadence_fade(self):
        """Testa fade de cadência com splits suficientes."""
        splits = create_splits(6, distance_each_m=2000.0, cadence=180, hr=150)
        # Segunda metade cadência menor
        for i in [3, 4, 5]:
            splits[i] = Split(
                idx=i+1, distance_m=2000, duration_s=600,
                pace=Pace.from_seconds_per_km(300),
                avg_hr=HeartRate(150), avg_cadence=Cadence(170),
                avg_temperature=None, elevation_m=None,
                intensity_type="ACTIVE", zone=ZoneKey("threshold"), km_label=f"{i+1},0"
            )

        activity = create_basic_activity(distance_m=12000.0, splits=splits)
        result = self.calc.calculate(activity, activity.splits)

        assert result is not None
        assert result.cadence_fade_spm is not None
        assert result.cadence_fade_spm < 0  # cadência caiu

    def test_no_cadence_fade_when_insufficient(self):
        """Sem fade quando < 2 voltas com cadência por metade."""
        splits = create_splits(4, cadence=180)  # 4 voltas (atende gate)
        # Uma sem cadência na primeira metade, uma na segunda
        splits[1] = Split(idx=2, distance_m=1000, duration_s=300,
                          pace=Pace.from_seconds_per_km(300),
                          avg_hr=HeartRate(150), avg_cadence=None,
                          avg_temperature=None, elevation_m=None,
                          intensity_type="ACTIVE", zone=ZoneKey("threshold"), km_label="2,0")
        splits[3] = Split(idx=4, distance_m=1000, duration_s=300,
                          pace=Pace.from_seconds_per_km(300),
                          avg_hr=HeartRate(150), avg_cadence=None,
                          avg_temperature=None, elevation_m=None,
                          intensity_type="ACTIVE", zone=ZoneKey("threshold"), km_label="4,0")

        activity = create_basic_activity(distance_m=8000.0, splits=splits)
        result = self.calc.calculate(activity, activity.splits)

        assert result is not None
        assert result.cadence_fade_spm is None


class TestInferType:
    def setup_method(self):
        self.zone_config = ZoneConfigVO(
            vdot=50.0,
            pace_zones={
                ZoneKey("easy"): (360, None),
                ZoneKey("marathon"): (300, 360),
                ZoneKey("threshold"): (240, 300),
                ZoneKey("interval"): (180, 240),
                ZoneKey("repetition"): (None, 180),
            },
            hr_zones={},
        )

    def _classify(self, splits: list[Split]) -> list[ClassifiedSplit]:
        return classify_splits(splits, self.zone_config)

    def test_race_priority(self):
        """Prova tem prioridade máxima."""
        splits = create_splits(3)
        classified = self._classify(splits)
        result = infer_type({"eventType": {"typeKey": "race"}}, classified, 5000)
        assert result == "prova"

    def test_intervalado_two_work_groups(self):
        """>= 2 grupos interval/repetition = intervalado."""
        splits = [
            Split(idx=1, distance_m=2000, duration_s=600, pace=Pace.from_seconds_per_km(300),
                  avg_hr=HeartRate(160), avg_cadence=Cadence(180),
                  avg_temperature=None, elevation_m=None,
                  intensity_type="INTERVAL", zone=ZoneKey("interval"), km_label="1,0"),
            Split(idx=2, distance_m=1000, duration_s=300, pace=Pace.from_seconds_per_km(300),
                  avg_hr=HeartRate(140), avg_cadence=Cadence(170),
                  avg_temperature=None, elevation_m=None,
                  intensity_type="RECOVERY", zone=ZoneKey("easy"), km_label="2,0"),
            Split(idx=3, distance_m=2000, duration_s=600, pace=Pace.from_seconds_per_km(300),
                  avg_hr=HeartRate(160), avg_cadence=Cadence(180),
                  avg_temperature=None, elevation_m=None,
                  intensity_type="INTERVAL", zone=ZoneKey("interval"), km_label="3,0"),
        ]
        classified = self._classify(splits)
        result = infer_type(None, classified, 5000)
        assert result == "intervalado"

    def test_limiar_block_threshold(self):
        """Bloco >=3 voltas threshold >=2000m = limiar."""
        splits = create_splits(4, zone="threshold", distance_each_m=800)  # 3.2km total
        classified = self._classify(splits)
        result = infer_type(None, classified, 3200)
        assert result == "limiar"

    def test_tempo_block_marathon(self):
        """Bloco >=3 voltas marathon >=2000m = tempo."""
        splits = create_splits(4, zone="marathon", distance_each_m=800)
        classified = self._classify(splits)
        result = infer_type(None, classified, 3200)
        assert result == "tempo"

    def test_progressivo(self):
        """2ª metade <= 92% do pace da 1ª = progressivo."""
        # First half 300 s/km, second half 270 s/km (faster) -> 90% ratio
        # Use "easy" zone to avoid matching marathon/threshold blocks
        splits = [
            Split(idx=1, distance_m=2500, duration_s=750, pace=Pace.from_seconds_per_km(300),
                  avg_hr=HeartRate(150), avg_cadence=Cadence(180),
                  avg_temperature=None, elevation_m=None,
                  intensity_type="ACTIVE", zone=ZoneKey("easy"), km_label="1,0"),
            Split(idx=2, distance_m=2500, duration_s=750, pace=Pace.from_seconds_per_km(300),
                  avg_hr=HeartRate(150), avg_cadence=Cadence(180),
                  avg_temperature=None, elevation_m=None,
                  intensity_type="ACTIVE", zone=ZoneKey("easy"), km_label="2,0"),
            Split(idx=3, distance_m=2500, duration_s=675, pace=Pace.from_seconds_per_km(270),
                  avg_hr=HeartRate(155), avg_cadence=Cadence(185),
                  avg_temperature=None, elevation_m=None,
                  intensity_type="ACTIVE", zone=ZoneKey("easy"), km_label="3,0"),
            Split(idx=4, distance_m=2500, duration_s=675, pace=Pace.from_seconds_per_km(270),
                  avg_hr=HeartRate(155), avg_cadence=Cadence(185),
                  avg_temperature=None, elevation_m=None,
                  intensity_type="ACTIVE", zone=ZoneKey("easy"), km_label="4,0"),
        ]
        classified = self._classify(splits)
        result = infer_type(None, classified, 10000)
        assert result == "progressivo"

    def test_longao(self):
        """>= 16km = longao (se não encaixa nos outros)."""
        splits = create_splits(16, distance_each_m=1000, zone="easy")
        classified = self._classify(splits)
        result = infer_type(None, classified, 16000)
        assert result == "longao"

    def test_facil_default(self):
        """Default = facil."""
        splits = create_splits(5, zone="easy", distance_each_m=1000)
        classified = self._classify(splits)
        result = infer_type(None, classified, 5000)
        assert result == "facil"


class TestDeriveStructure:
    def setup_method(self):
        self.zone_config = ZoneConfigVO(
            vdot=50.0,
            pace_zones={
                ZoneKey("easy"): (360, None),
                ZoneKey("marathon"): (300, 360),
                ZoneKey("threshold"): (240, 300),
                ZoneKey("interval"): (180, 240),
                ZoneKey("repetition"): (None, 180),
            },
            hr_zones={},
        )

    def _classify(self, splits: list[Split]) -> list[ClassifiedSplit]:
        return classify_splits(splits, self.zone_config)

    def test_single_intensity(self):
        """Todas voltas mesmo tipo = rótulo único."""
        splits = create_splits(4, intensity="ACTIVE")
        classified = self._classify(splits)
        result = derive_structure(classified)
        assert result == "Corrida"

    def test_multiple_intensities(self):
        """Intensidades diferentes = soma formatada."""
        splits = [
            Split(idx=1, distance_m=2000, duration_s=600, pace=Pace.from_seconds_per_km(300),
                  avg_hr=HeartRate(140), avg_cadence=Cadence(170),
                  avg_temperature=None, elevation_m=None,
                  intensity_type="WARMUP", zone=ZoneKey("easy"), km_label="1,0"),
            Split(idx=2, distance_m=5000, duration_s=1500, pace=Pace.from_seconds_per_km(300),
                  avg_hr=HeartRate(155), avg_cadence=Cadence(180),
                  avg_temperature=None, elevation_m=None,
                  intensity_type="ACTIVE", zone=ZoneKey("marathon"), km_label="2,0"),
            Split(idx=3, distance_m=2000, duration_s=600, pace=Pace.from_seconds_per_km(300),
                  avg_hr=HeartRate(140), avg_cadence=Cadence(170),
                  avg_temperature=None, elevation_m=None,
                  intensity_type="COOLDOWN", zone=ZoneKey("easy"), km_label="3,0"),
        ]
        classified = self._classify(splits)
        result = derive_structure(classified)
        assert "Aquecimento 2,0km" in result
        assert "Corrida 5,0km" in result
        assert "Desaquecimento 2,0km" in result

    def test_none_when_no_intensity(self):
        """None quando nenhuma volta tem intensity_type."""
        splits = create_splits(4, intensity=None)
        classified = self._classify(splits)
        result = derive_structure(classified)
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])