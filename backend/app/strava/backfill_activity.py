"""Backfill de running dynamics por atividade, sob demanda (CLI).

Enriquece os splits de uma corrida já sincronizada com running dynamics
(GCT, passada, oscilação, ratio) do Garmin Connect — um activity_id por
execução, sem re-pull de listagens. Commit único no fim (tudo-ou-nada),
idempotente por upsert (activity_id, idx).

Uso:
    python -m app.strava.backfill_activity --activity-id 12345 --user-id 1 [--yes]
"""

import argparse
import sys
from typing import Callable

from sqlalchemy import select

from app.db.engine import SessionLocal
from app.db.models import Activity, Split
from app.garmin.client import GarminGateway
from app.garmin.mappers import RUNNING_TYPES, map_splits


class BackfillActivityError(Exception):
    """Erro de domínio do backfill por atividade."""


def backfill_activity(
    db,
    user_id: int,
    activity_id: int,
    fetch_typed_splits: Callable[[int], dict | None] | None = None,
    yes: bool = False,
) -> dict:
    """Enriquece os splits da `activity_id` com running dynamics do Garmin.

    `fetch_typed_splits` é injetável (default: GarminGateway real a partir
    dos tokens do usuário no banco). Retorna dict com o resumo da execução.
    """
    activity = (
        db.execute(
            select(Activity).where(
                Activity.id == activity_id, Activity.user_id == user_id
            )
        )
    ).scalar_one_or_none()
    if activity is None:
        raise BackfillActivityError(
            f"Atividade {activity_id} não encontrada para o usuário {user_id}"
        )

    if activity.activity_type not in RUNNING_TYPES:
        return {
            "activity_id": activity_id,
            "skipped": "not_running",
            "message": "atividade não é corrida (running/trail_running)",
        }

    if fetch_typed_splits is None:
        gateway = GarminGateway.from_user(db, user_id)

        def fetch_typed_splits(aid: int) -> dict | None:  # noqa: D401
            return gateway.get_activity_splits_typed(aid)

    payload = fetch_typed_splits(activity_id) or {}
    laps = payload.get("lapDTOs") or [] if isinstance(payload, dict) else payload or []
    mapped = map_splits(laps)  # aceita lista direta de lapDTOs
    by_idx = {m["idx"]: m for m in mapped}

    splits = (
        db.execute(
            select(Split).where(Split.activity_id == activity_id).order_by(Split.idx)
        )
    ).scalars().all()

    updated = 0
    for split in splits:
        m = by_idx.get(split.idx)
        if m is None:
            continue
        split.ground_contact_time_ms = m.get("ground_contact_time_ms")
        split.stride_length_cm = m.get("stride_length_cm")
        split.vertical_oscillation_cm = m.get("vertical_oscillation_cm")
        split.vertical_ratio = m.get("vertical_ratio")
        updated += 1

    db.commit()
    return {
        "activity_id": activity_id,
        "activity_type": activity.activity_type,
        "splits_updated": updated,
        "laps_returned": len(laps),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Backfill de running dynamics por atividade (sob demanda)."
    )
    parser.add_argument("--activity-id", type=int, required=True, help="ID da atividade no Ritmo")
    parser.add_argument("--user-id", type=int, default=1, help="ID do usuário (default 1)")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="confirma execução sem prompt interativo",
    )
    args = parser.parse_args(argv)

    if not args.yes:
        confirm = input(
            f"Enriquecer running dynamics da atividade {args.activity_id} "
            f"(usuário {args.user_id})? [y/N]: "
        )
        if confirm.strip().lower() != "y":
            print("Cancelado.")
            return 0

    with SessionLocal() as db:
        try:
            result = backfill_activity(db, args.user_id, args.activity_id, yes=args.yes)
        except BackfillActivityError as exc:
            print(f"Erro: {exc}")
            return 1

    print(
        f"Atividade {result['activity_id']} ({result['activity_type']}): "
        f"{result['splits_updated']} splits atualizados de "
        f"{result['laps_returned']} lapDTOs retornados."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
