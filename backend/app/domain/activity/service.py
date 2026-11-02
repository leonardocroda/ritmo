"""Application Service (Use Cases) do domínio Activities."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Optional

from app.domain.activity.domain.entities import Activity, Split
from app.domain.activity.domain.services import (
    ConsistencyCalculator,
    ConsistencyMetrics,
    infer_type,
    derive_structure,
    classify_splits,
    ClassifiedSplit,
)
from app.domain.activity.domain.value_objects import (
    ActivityFilter,
    ZoneConfigVO,
    ZoneKey,
)
from app.domain.activity.ports.repositories import ActivityRepository, SplitRepository
from app.domain.activity.ports.zone_config import ZoneConfigProvider
from app.domain.activity.schemas import (
    ActivityDetailOut,
    ActivityListOut,
    ActivityListItemOut,
    ActivityOut,
    SplitOut,
    ZoneMetaOut,
    ConsistencyOut,
    ContextOut,
    ShoeSummaryOut,
)


@dataclass
class ActivityService:
    """Service de aplicação que orquestra repositórios e serviços de domínio."""

    repo: ActivityRepository
    split_repo: SplitRepository
    zone_provider: ZoneConfigProvider
    consistency: ConsistencyCalculator

    def get_detail(self, activity_id: int, user_id: int) -> Optional[ActivityDetailOut]:
        """Obtém detalhe completo de uma atividade."""
        activity = self.repo.get_by_id(activity_id, user_id)
        if not activity:
            return None

        splits = self.split_repo.get_by_activity(activity_id)
        zone_config = self.zone_provider.get_for_user(user_id)

        # Classifica splits por zona
        classified = classify_splits(splits, zone_config)

        # Calcula consistência
        consistency_metrics = self.consistency.calculate(activity, splits)

        # Infere tipo e estrutura
        inferred = infer_type(None, classified, activity.distance_m)
        structure = derive_structure(classified)

        # Converte para DTOs de saída
        activity_out = self._to_activity_out(activity, inferred, structure)
        splits_out = self._to_splits_out(splits, zone_config)
        zones_out = self._to_zones_out(zone_config)
        consistency_out = self._to_consistency_out(consistency_metrics)
        context_out = self._to_context_out(activity, splits, user_id)
        shoe_out = self._to_shoe_out(activity)

        return ActivityDetailOut(
            activity=activity_out,
            splits=splits_out,
            zones=zones_out,
            hr_color="#f8fafc",
            consistency=consistency_out,
            context=context_out,
            evaluations=[],  # TODO: buscar avaliações
            shoe=shoe_out,
        )

    def list(
        self,
        user_id: int,
        filter: ActivityFilter,
        limit: int,
        offset: int,
    ) -> ActivityListOut:
        """Lista atividades paginada."""
        activities = self.repo.list(user_id, filter)
        total = self.repo.count(user_id, filter)
        zone_config = self.zone_provider.get_for_user(user_id)

        items = [self._to_list_item_out(a, zone_config) for a in activities]
        return ActivityListOut(items=items, total=total, limit=limit, offset=offset)

    # --- Helpers de conversão para DTOs ---

    def _to_activity_out(
        self,
        activity: Activity,
        inferred_type: str,
        structure: Optional[str],
    ) -> ActivityOut:
        return ActivityOut(
            id=activity.id,
            start_time=activity.start_time,
            activity_type=activity.activity_type,
            name=activity.name,
            distance_m=activity.distance_m,
            duration_s=activity.duration_s,
            pace_s=float(activity.pace) if activity.pace else None,
            avg_hr=activity.avg_hr.bpm if activity.avg_hr else None,
            max_hr=activity.max_hr.bpm if activity.max_hr else None,
            avg_cadence=activity.avg_cadence.spm if activity.avg_cadence else None,
            elevation_gain_m=activity.elevation_gain_m,
            aerobic_te=activity.aerobic_te,
            anaerobic_te=activity.anaerobic_te,
            training_load=activity.training_load,
            evaluated=activity.evaluated,
            inferred_type=inferred_type,
            structure=structure,
        )

    def _to_list_item_out(
        self,
        activity: Activity,
        zone_config: ZoneConfigVO,
    ) -> ActivityListItemOut:
        return ActivityListItemOut(
            id=activity.id,
            start_time=activity.start_time,
            activity_type=activity.activity_type,
            name=activity.name,
            distance_m=activity.distance_m,
            duration_s=activity.duration_s,
            pace_s=float(activity.pace) if activity.pace else None,
            avg_hr=activity.avg_hr.bpm if activity.avg_hr else None,
            inferred_type=infer_type(None, classify_splits(activity.splits, zone_config), activity.distance_m),
            evaluated=activity.evaluated,
        )

    def _to_splits_out(self, splits: Sequence[Split], zone_config: ZoneConfigVO) -> list[SplitOut]:
        out = []
        for split in splits:
            pace_s = float(split.pace) if split.pace else None
            zone = zone_config.classify_pace(pace_s) if pace_s else None
            out.append(
                SplitOut(
                    idx=split.idx,
                    dist_m=split.distance_m,
                    duration_s=split.duration_s,
                    pace_s=pace_s,
                    avg_hr=split.avg_hr.bpm if split.avg_hr else None,
                    avg_cadence=split.avg_cadence.spm if split.avg_cadence else None,
                    avg_temperature=split.avg_temperature,
                    elevation_m=split.elevation_m,
                    intensity_type=split.intensity_type,
                    zone=zone if zone else None,
                    km_label=split.km_label,
                )
            )
        return out

    def _to_zones_out(self, zone_config: ZoneConfigVO) -> list[ZoneMetaOut]:
        # Mapeia cores por zona (mesmo design do backend original)
        colors = {
            "easy": "#22c55e",
            "marathon": "#3b82f6",
            "threshold": "#f97316",
            "interval": "#ef4444",
            "repetition": "#a855f7",
        }
        labels = {
            "easy": "Easy",
            "marathon": "Maratona",
            "threshold": "Limiar",
            "interval": "Intervalado",
            "repetition": "Repetição",
        }

        zones = []
        for zone_key in ZoneKey.VALID:
            zone = zone_key  # zone_key is already a string
            # Extrai pace range do zone_config
            min_pace, max_pace = zone_config.pace_zones.get(zone, (None, None))
            if min_pace and max_pace:
                pace_range = f"{int(min_pace//60)}:{int(min_pace%60):02d}-{int(max_pace//60)}:{int(max_pace%60):02d}/km"
            elif min_pace:
                pace_range = f"{int(min_pace//60)}:{int(min_pace%60):02d}+/km"
            elif max_pace:
                pace_range = f"-{int(max_pace//60)}:{int(max_pace%60):02d}/km"
            else:
                pace_range = "—"

            zones.append(
                ZoneMetaOut(
                    key=zone,
                    label=labels.get(zone, zone),
                    pace_range=pace_range,
                    color=colors.get(zone, "#888888"),
                )
            )
        return zones

    def _to_consistency_out(self, metrics: Optional[ConsistencyMetrics]) -> Optional[ConsistencyOut]:
        if metrics is None:
            return None
        return ConsistencyOut(
            first_half_pace_s=metrics.first_half_pace_s,
            second_half_pace_s=metrics.second_half_pace_s,
            balance_delta_s=metrics.balance_delta_s,
            balance_delta_pct=metrics.balance_delta_pct,
            first_half_hr=metrics.first_half_hr,
            second_half_hr=metrics.second_half_hr,
            hr_drift_bpm=metrics.hr_drift_bpm,
            decoupling_pct=metrics.decoupling_pct,
            cadence_fade_spm=metrics.cadence_fade_spm,
        )

    def _to_context_out(self, activity: Activity, splits: Sequence[Split], user_id: int) -> ContextOut:
        # TODO: buscar sono, HRV, RHR do repositório de health
        # Por enquanto retorna vazio
        return ContextOut()

    def _to_shoe_out(self, activity: Activity) -> Optional[ShoeSummaryOut]:
        if activity.shoe_id is None:
            return None
        # TODO: buscar tênis do repositório
        return None