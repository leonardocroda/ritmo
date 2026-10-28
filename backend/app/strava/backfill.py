#!/usr/bin/env python3
"""CLI de backfill one-shot Strava → Ritmo (feature tenis).

Execução única que:
1. Resolve token (--code via OAuth OU --token direto)
2. Busca shoes + runs do atleta (paginado, filtra Run)
3. Upsert tênis por strava_gear_id
4. Para cada run com gear_id: matching (external_id → fallback) + associação retroativa
5. initial_km = max(0, km_strava - Σ casadas)
6. Commit único no fim (tudo-ou-nada; re-run idempotente)
7. Relatório com checksum por tênis

OAuth manual (rodar antes da 1ª vez):
1. Crie app em https://strava.com/settings/api
   - Application Name: Ritmo Backfill
   - Redirect URI: http://localhost:8080/callback
   - Scopes: profile:read_all, activity:read_all
2. Acesse a URL de autorização (substitua CLIENT_ID):
   https://www.strava.com/oauth/authorize?client_id=CLIENT_ID&response_type=code&redirect_uri=http://localhost:8080/callback&approval_prompt=force&scope=profile:read_all,activity:read_all
3. Autorize e copie o `code` da URL de callback (ex: http://localhost:8080/callback?code=ABC123&scope=...)
4. Rode: python -m app.strava.backfill --code ABC123

Uso:
  python -m app.strava.backfill --code CODE [--user-id 1] [--yes]
  python -m app.strava.backfill --token TOKEN [--user-id 1] [--yes]

Flags:
  --code CODE       Authorization code do OAuth (exclusivo com --token)
  --token TOKEN     Access token direto (exclusivo com --code)
  --user-id ID      Usuário alvo (default: 1)
  --yes             Pula confirmação interativa
"""

import argparse
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.engine import SessionLocal
from app.db.models import Activity, Shoe, User
from app.garmin.mappers import RUNNING_TYPES
from app.strava.client import (
    StravaClientError,
    exchange_code,
    fetch_athlete_shoes,
    fetch_run_activities,
)
from app.strava.matching import find_match, garmin_id_from_external_id


@dataclass
class ShoeReport:
    """Relatório por tênis para o checksum final."""

    strava_gear_id: str
    name: str
    strava_distance_km: float  # distance do gear no Strava
    matched_runs_km: float = 0.0  # soma das runs casadas
    unmatched_runs_km: float = 0.0  # runs sem match (sem gear_id ou não casaram)
    initial_km: float = 0.0
    created: bool = False
    updated: bool = False


class BackfillError(Exception):
    """Erro de domínio do backfill — mensagem segura, sem token."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


def _confirm(prompt: str, default_yes: bool = False) -> bool:
    """Confirmação interativa."""
    suffix = " [S/n]" if default_yes else " [s/N]"
    try:
        resp = input(f"{prompt}{suffix}: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nAbortado pelo usuário.")
        sys.exit(1)
    if not resp:
        return default_yes
    return resp in ("s", "sim", "y", "yes")


def _resolve_token(code: str | None, token: str | None) -> str:
    """Resolve access token: troca code ou usa token direto."""
    if code and token:
        raise BackfillError("Use --code OU --token, não ambos")
    if not code and not token:
        raise BackfillError("Informe --code (OAuth) ou --token (direto)")

    if code:
        print("Trocando authorization code por access token...")
        return exchange_code(code)
    return token


def _fetch_strava_data(token: str) -> tuple[list[dict], list[dict]]:
    """Busca shoes e runs do Strava."""
    print("Buscando tênis do atleta...")
    shoes = fetch_athlete_shoes(token)
    print(f"  {len(shoes)} tênis encontrados")

    print("Buscando atividades de corrida (paginado)...")
    runs = fetch_run_activities(token)
    print(f"  {len(runs)} corridas encontradas")
    return shoes, runs


def _upsert_shoes(
    db: Session, user_id: int, strava_shoes: list[dict]
) -> dict[str, Shoe]:
    """Upsert tênis por strava_gear_id. Retorna mapa gear_id -> Shoe."""
    gear_to_shoe: dict[str, Shoe] = {}

    for s in strava_shoes:
        gear_id = s["id"]
        existing = db.execute(
            select(Shoe).where(Shoe.user_id == user_id, Shoe.strava_gear_id == gear_id)
        ).scalar_one_or_none()

        if existing:
            # Atualiza nome/brand/model se mudou
            existing.name = s.get("name", existing.name)
            existing.brand = s.get("brand_name", existing.brand)
            existing.model = s.get("model_name", existing.model)
            gear_to_shoe[gear_id] = existing
        else:
            shoe = Shoe(
                user_id=user_id,
                name=s.get("name", f"Tênis {gear_id}"),
                brand=s.get("brand_name"),
                model=s.get("model_name"),
                status="ativo",
                strava_gear_id=gear_id,
                initial_km=0.0,  # será ajustado depois
            )
            db.add(shoe)
            db.flush()
            gear_to_shoe[gear_id] = shoe

    return gear_to_shoe


def _match_and_associate(
    db: Session,
    user_id: int,
    strava_runs: list[dict],
    gear_to_shoe: dict[str, Shoe],
    reports: dict[str, ShoeReport],
) -> tuple[int, int, int, int]:
    """Matching e associação retroativa.

    Returns:
        (matched_count, unmatched_no_gear, unmatched_no_match, ambiguous_count)
    """
    # Pre-carrega todas as atividades do usuário (corridas) para matching
    activities = db.execute(
        select(Activity).where(
            Activity.user_id == user_id, Activity.activity_type.in_(RUNNING_TYPES)
        )
    ).scalars().all()

    # Índice por garmin_id (external_id)
    by_garmin_id = {}
    for a in activities:
        if a.garmin_id:
            by_garmin_id[a.garmin_id] = a

    matched = 0
    unmatched_no_gear = 0
    unmatched_no_match = 0
    ambiguous = 0

    for run in strava_runs:
        gear_id = run.get("gear_id")
        run_distance_km = run.get("distance", 0.0) / 1000.0

        if not gear_id:
            unmatched_no_gear += 1
            # Acumula no relatório "sem gear_id" - usamos chave especial
            if "__no_gear__" not in reports:
                reports["__no_gear__"] = ShoeReport(
                    strava_gear_id="__no_gear__",
                    name="(sem gear_id)",
                    strava_distance_km=0,
                )
            reports["__no_gear__"].unmatched_runs_km += run_distance_km
            continue

        shoe = gear_to_shoe.get(gear_id)
        if not shoe:
            # Tênis não foi upsertado (não deveria acontecer)
            unmatched_no_gear += 1
            continue

        # Tenta match por external_id primeiro
        external_id = run.get("external_id")
        activity = None
        match_method = None

        if external_id:
            garmin_id = garmin_id_from_external_id(external_id)
            if garmin_id and garmin_id in by_garmin_id:
                activity = by_garmin_id[garmin_id]
                match_method = "external_id"

        # Fallback heurístico
        if activity is None:
            candidates = [
                {
                    "id": a.id,
                    "distance_m": a.distance_m,
                    "duration_s": a.duration_s,
                    "start_time": a.start_time,
                }
                for a in activities
                if a.shoe_id is None  # só associa atividades SEM tênis
            ]
            match_result = find_match(run, candidates)
            if isinstance(match_result, int):
                activity = db.get(Activity, match_result)
                match_method = "fallback"
            elif match_result == "ambiguous":
                ambiguous += 1
                reports[gear_id].unmatched_runs_km += run_distance_km
                continue

        if activity is None:
            unmatched_no_match += 1
            reports[gear_id].unmatched_runs_km += run_distance_km
            continue

        # Associa retroativamente
        if activity.shoe_id is not None:
            # Já tem tênis - não sobrescreve (segurança)
            unmatched_no_match += 1
            reports[gear_id].unmatched_runs_km += run_distance_km
            continue

        activity.shoe_id = shoe.id
        db.flush()
        matched += 1
        reports[gear_id].matched_runs_km += run_distance_km

    return matched, unmatched_no_gear, unmatched_no_match, ambiguous


def _adjust_initial_km(
    db: Session, gear_to_shoe: dict[str, Shoe], reports: dict[str, ShoeReport]
) -> None:
    """Ajusta initial_km = max(0, km_strava - Σ casadas) para cada tênis."""
    for gear_id, shoe in gear_to_shoe.items():
        report = reports.get(gear_id)
        if not report:
            continue
        strava_km = report.strava_distance_km
        matched_km = report.matched_runs_km
        initial = max(0.0, strava_km - matched_km)
        shoe.initial_km = round(initial, 2)
        report.initial_km = shoe.initial_km


def _print_report(
    gear_to_shoe: dict[str, Shoe], reports: dict[str, ShoeReport], strava_shoes: list[dict]
) -> None:
    """Imprime relatório final com checksum."""
    print("\n" + "=" * 60)
    print("RELATÓRIO DE BACKFILL")
    print("=" * 60)

    total_strava = 0.0
    total_initial = 0.0
    total_matched = 0.0
    total_unmatched = 0.0

    for s in strava_shoes:
        gear_id = s["id"]
        report = reports.get(gear_id)
        if not report:
            continue

        shoe = gear_to_shoe[gear_id]
        status = "criado" if report.created else ("atualizado" if report.updated else "inalterado")

        print(f"\n👟 {shoe.name} ({gear_id}) — {status}")
        print(f"   km Strava (gear):     {report.strava_distance_km:.2f} km")
        print(f"   km casadas (match):   {report.matched_runs_km:.2f} km")
        print(f"   km não casadas:       {report.unmatched_runs_km:.2f} km")
        print(f"   initial_km (ajustada): {report.initial_km:.2f} km")

        # Checksum
        checksum = report.initial_km + report.matched_runs_km + report.unmatched_runs_km
        diff = abs(checksum - report.strava_distance_km)
        ok = "✓" if diff <= 0.1 else "✗"
        print(f"   CHECKSUM: {checksum:.2f} vs Strava {report.strava_distance_km:.2f} {ok}")

        total_strava += report.strava_distance_km
        total_initial += report.initial_km
        total_matched += report.matched_runs_km
        total_unmatched += report.unmatched_runs_km

    # Gear_id não encontrado no upsert (runs sem gear_id)
    if "__no_gear__" in reports:
        report = reports["__no_gear__"]
        print(f"\n❓ Corridas sem gear_id: {report.unmatched_runs_km:.2f} km")
        total_unmatched += report.unmatched_runs_km

    print("\n" + "-" * 60)
    print(f"TOTAL Strava (gear):     {total_strava:.2f} km")
    print(f"TOTAL initial_km:        {total_initial:.2f} km")
    print(f"TOTAL casadas:           {total_matched:.2f} km")
    print(f"TOTAL não alocada:       {total_unmatched:.2f} km")
    total_checksum = total_initial + total_matched + total_unmatched
    total_diff = abs(total_checksum - total_strava)
    ok = "✓" if total_diff <= 0.1 else "✗"
    print(f"CHECSUM GLOBAL:          {total_checksum:.2f} vs {total_strava:.2f} {ok}")
    print("=" * 60)


def run_backfill(
    code: str | None = None,
    token: str | None = None,
    user_id: int = 1,
    yes: bool = False,
) -> None:
    """Executa o backfill completo."""
    try:
        # 1. Resolve token
        access_token = _resolve_token(code, token)

        # 2. Busca dados do Strava
        strava_shoes, strava_runs = _fetch_strava_data(access_token)

        # 3. Prepara relatórios
        reports: dict[str, ShoeReport] = {}
        for s in strava_shoes:
            gear_id = s["id"]
            distance_km = s.get("distance", 0.0) / 1000.0
            reports[gear_id] = ShoeReport(
                strava_gear_id=gear_id,
                name=s.get("name", gear_id),
                strava_distance_km=distance_km,
            )

        # 4. Executa no banco (transação única)
        with SessionLocal() as db:
            # Verifica usuário
            user = db.get(User, user_id)
            if not user:
                raise BackfillError(f"Usuário {user_id} não encontrado")

            # Upsert tênis
            gear_to_shoe = _upsert_shoes(db, user_id, strava_shoes)

            # Marca created/updated nos relatórios
            for gear_id, shoe in gear_to_shoe.items():
                if gear_id in reports:
                    # Verifica se era novo (id gerado agora vs existente)
                    # Simplificação: se initial_km era 0 e created_at é recente, considera created
                    reports[gear_id].created = shoe.created_at is not None and shoe.initial_km == 0

            # Matching + associação
            matched, no_gear, no_match, ambig = _match_and_associate(
                db, user_id, strava_runs, gear_to_shoe, reports
            )

            # Ajusta initial_km
            _adjust_initial_km(db, gear_to_shoe, reports)

            # Preview
            print("\n--- PREVIEW ---")
            print(f"Tênis a criar/atualizar: {len(gear_to_shoe)}")
            print(f"Corridas a associar:     {matched}")
            print(f"Sem gear_id:             {no_gear}")
            print(f"Sem match:               {no_match}")
            print(f"Ambiguidade:             {ambig}")

            if not yes:
                if not _confirm("Confirmar e commitar?", default_yes=True):
                    print("Abortado — nenhuma alteração gravada.")
                    return

            # Commit único
            db.commit()
            print("\n✓ Commit realizado com sucesso.")

        # 5. Relatório final (fora da transação)
        _print_report(gear_to_shoe, reports, strava_shoes)

    except StravaClientError as exc:
        raise BackfillError(str(exc)) from exc


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill one-shot Strava → Ritmo (tênis + associação retroativa)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--code", help="Authorization code do OAuth Strava")
    group.add_argument("--token", help="Access token direto do Strava")
    parser.add_argument("--user-id", type=int, default=1, help="ID do usuário alvo (default: 1)")
    parser.add_argument("--yes", action="store_true", help="Pula confirmação interativa")
    args = parser.parse_args()

    try:
        run_backfill(code=args.code, token=args.token, user_id=args.user_id, yes=args.yes)
    except (BackfillError, StravaClientError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrompido pelo usuário.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()