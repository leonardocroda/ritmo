#!/usr/bin/env python3
"""
Script de backfill do Garmin — busca atividades desde 01/01/2025 e splits de atividades existentes.

Uso:
    python -m backend.scripts.garmin_backfill [--user-id 1] [--from-date 2025-01-01] [--only-splits]

Opções:
    --user-id      ID do usuário (padrão: 1)
    --from-date    Data inicial para buscar atividades (padrão: 2025-01-01)
    --only-splits  Apenas buscar splits das atividades já existentes no banco (não puxa atividades novas)
    --dry-run      Não grava no banco, apenas mostra o que faria
"""

import argparse
import time
from datetime import date, datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, DisconnectionError

from app.core.config import get_settings
from app.db.engine import SessionLocal
from app.db.models import Activity, Split
from app.garmin.client import GarminGateway, GarminAuthExpiredError
from app.garmin.mappers import is_running, map_activity, map_splits
from app.garmin.upserts import upsert_activity, upsert_splits, get_sync_state, set_sync_state


# Configuração de batch
BATCH_SIZE = 50  # Commit a cada N atividades
MAX_DB_RETRIES = 3
DB_RETRY_DELAY_S = 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill Garmin activities and splits")
    parser.add_argument("--user-id", type=int, default=1, help="User ID (default: 1)")
    parser.add_argument("--from-date", type=str, default="2025-01-01", help="Start date YYYY-MM-DD (default: 2025-01-01)")
    parser.add_argument("--only-splits", action="store_true", help="Only fetch splits for existing activities")
    parser.add_argument("--dry-run", action="store_true", help="Don't write to database, just show what would be done")
    return parser.parse_args()


def _activity_db_id(db: Session, user_id: int, garmin_id: str) -> int:
    """Get internal activity ID from garmin_id."""
    return db.execute(
        select(Activity.id).where(
            Activity.user_id == user_id, Activity.garmin_id == garmin_id
        )
    ).scalar_one()


def _commit_with_retry(db: Session, operation_name: str, dry_run: bool = False) -> bool:
    """Commit with retry on connection errors."""
    if dry_run:
        return True
    
    for attempt in range(MAX_DB_RETRIES):
        try:
            db.commit()
            return True
        except (OperationalError, DisconnectionError) as e:
            if attempt < MAX_DB_RETRIES - 1:
                print(f"   ⚠️  Erro de conexão no {operation_name} (tentativa {attempt + 1}/{MAX_DB_RETRIES}): {e}")
                print(f"      Aguardando {DB_RETRY_DELAY_S}s e reconectando...")
                time.sleep(DB_RETRY_DELAY_S)
                # Rollback the failed transaction
                db.rollback()
                continue
            else:
                print(f"   ❌ Falha no {operation_name} após {MAX_DB_RETRIES} tentativas: {e}")
                db.rollback()
                return False
    return False


def backfill_activities(
    db: Session,
    gateway: GarminGateway,
    user_id: int,
    start_date: date,
    end_date: date,
    dry_run: bool = False,
) -> tuple[int, int, int]:
    """
    Fetch and upsert activities from Garmin for the date range.
    Returns (new_count, updated_count, oldest_date).
    """
    print(f"🔄 Buscando atividades de {start_date} a {end_date}...")
    raws = gateway.get_activities(start_date, end_date)
    print(f"   Encontradas {len(raws)} atividades no Garmin")

    new_count = 0
    updated_count = 0
    oldest = end_date
    batch_counter = 0

    for i, raw in enumerate(raws):
        data = map_activity(raw)
        status = upsert_activity(db, user_id, data)
        if status == "new":
            new_count += 1
            print(f"   ➕ Nova: {data['name']} ({data['start_time'].date()}) - {data['distance_m']/1000:.2f}km")
        else:
            updated_count += 1
            print(f"   🔄 Atualizada: {data['name']} ({data['start_time'].date()})")

        oldest = min(oldest, data["start_time"].date())
        batch_counter += 1

        # Commit em lote a cada BATCH_SIZE atividades
        if not dry_run and batch_counter >= BATCH_SIZE:
            print(f"   💾 Commit do lote ({new_count + updated_count} atividades processadas)...")
            if not _commit_with_retry(db, f"lote de atividades ({i+1}/{len(raws)})", dry_run):
                raise RuntimeError("Falha ao commitar lote de atividades")
            batch_counter = 0

    # Commit final do último lote
    if not dry_run and batch_counter > 0:
        print(f"   💾 Commit final ({new_count + updated_count} atividades total)...")
        if not _commit_with_retry(db, "lote final de atividades", dry_run):
            raise RuntimeError("Falha ao commitar lote final de atividades")
        set_sync_state(db, user_id, "activities", end_date)
        db.commit()

    return new_count, updated_count, oldest


def backfill_splits(
    db: Session,
    gateway: GarminGateway,
    user_id: int,
    dry_run: bool = False,
) -> tuple[int, int]:
    """
    Fetch and upsert splits for all running activities that don't have splits yet.
    Returns (activities_with_splits_added, total_splits_added).
    """
    # Find all running activities that don't have splits
    activities = db.execute(
        select(Activity).where(
            Activity.user_id == user_id,
            Activity.activity_type.in_(("running", "trail_running")),
        )
    ).scalars().all()

    print(f"🔍 Verificando splits para {len(activities)} atividades de corrida...")

    activities_with_splits = 0
    total_splits = 0

    for activity in activities:
        # Check if splits already exist
        existing_splits = db.execute(
            select(Split).where(Split.activity_id == activity.id)
        ).scalars().all()

        if existing_splits:
            continue  # Already has splits

        print(f"   📥 Buscando splits para atividade {activity.garmin_id} ({activity.start_time.date()})...")
        try:
            splits_raw = gateway.get_splits(int(activity.garmin_id))
            if splits_raw:
                splits = map_splits(splits_raw)
                if splits:
                    count = upsert_splits(db, activity.id, splits)
                    if not dry_run:
                        if not _commit_with_retry(db, f"splits da atividade {activity.garmin_id}", dry_run):
                            print(f"      ❌ Falha ao salvar splits")
                            continue
                    activities_with_splits += 1
                    total_splits += count
                    print(f"      ✅ {count} splits salvos")
                else:
                    print(f"      ⚠️  Sem splits no Garmin")
            else:
                print(f"      ⚠️  Atividade sem splits no Garmin")
        except Exception as e:
            print(f"      ❌ Erro ao buscar splits: {e}")
            if not dry_run:
                db.rollback()

    return activities_with_splits, total_splits


def main() -> None:
    args = parse_args()
    settings = get_settings()
    start_date = date.fromisoformat(args.from_date)
    end_date = date.today()

    print("=" * 60)
    print("🏃 GARMIN BACKFILL")
    print("=" * 60)
    print(f"Usuário: {args.user_id}")
    print(f"Período: {start_date} a {end_date}")
    print(f"Modo: {'Apenas splits' if args.only_splits else 'Atividades + splits'}")
    print(f"Dry-run: {'Sim' if args.dry_run else 'Não'}")
    print(f"Tamanho do lote: {BATCH_SIZE} atividades/commit")
    print("=" * 60)

    if args.dry_run:
        print("⚠️  MODO DRY-RUN: nenhuma alteração será gravada no banco\n")

    try:
        # Usar sessão nova para cada fase principal para evitar transações longas
        if not args.only_splits:
            # Fase 1: Backfill activities
            with SessionLocal() as db:
                gateway = GarminGateway.from_user(db, args.user_id, settings)
                print(f"✅ Conectado ao Garmin (chamadas feitas: {gateway.calls_made})")

                new_count, updated_count, oldest = backfill_activities(
                    db, gateway, args.user_id, start_date, end_date, args.dry_run
                )
                print(f"\n📊 Atividades: {new_count} novas, {updated_count} atualizadas")
                print(f"   Data mais antiga tocada: {oldest}")

            # Fase 2: Backfill splits (nova sessão)
            print()
            with SessionLocal() as db:
                gateway = GarminGateway.from_user(db, args.user_id, settings)
                split_activities, split_count = backfill_splits(db, gateway, args.user_id, args.dry_run)
                print(f"\n📊 Splits: {split_activities} atividades receberam splits, {split_count} splits total")

        else:
            # Apenas splits
            with SessionLocal() as db:
                gateway = GarminGateway.from_user(db, args.user_id, settings)
                print(f"✅ Conectado ao Garmin (chamadas feitas: {gateway.calls_made})")
                split_activities, split_count = backfill_splits(db, gateway, args.user_id, args.dry_run)
                print(f"\n📊 Splits: {split_activities} atividades receberam splits, {split_count} splits total")

        print(f"\n✅ Concluído!")

    except GarminAuthExpiredError as e:
        print(f"\n❌ Erro de autenticação: {e}")
        print("   Rode: python -m app.garmin.login --user <seu_email>")
        exit(1)
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()