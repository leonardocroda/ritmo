"use client";

// Chips de roteamento (mock v0.3 §03, chips3) — um dado, um verbo, um
// destino (legend 5): a Home roteia, nunca duplica painéis. Último
// treino -> /treinos/{id} (selo "avaliado ✓" quando evaluated), volume
// e countdown -> /performance. Chip sem dado é OMITIDO, não renderiza
// estado vazio (HOME-24) — dado que não existe não ocupa lugar. Alvo de
// toque ≥44px (HOME-36): nada de link decorativo.

import Link from "next/link";
import type { ReactNode } from "react";

import type { HomeCountdown, HomeLastActivity, HomeVolume } from "@/lib/api";
import { formatKm } from "@/lib/format";

/** Delta % com sinal e vírgula PT-BR: 8 -> "+8%", -8.3 -> "−8,3%". */
function formatDeltaPct(deltaPct: number): string {
  const sign = deltaPct > 0 ? "+" : deltaPct < 0 ? "−" : "";
  const rounded = Math.round(deltaPct * 10) / 10;
  const text = Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
  return `${sign}${text.replace(".", ",")}%`;
}

/** Data-only ISO em dias corridos desde a epoch — sem `new Date(iso)`
 * (UTC atrasaria um dia em fuso negativo; wall clock é a premissa). */
function epochDays(iso: string): number {
  const [year, month, day] = iso.split("-").map(Number);
  return Date.UTC(year, month - 1, day) / 86_400_000;
}

/** Data relativa do último treino: "hoje", "ontem", "há N dias". */
function relativeDate(activityIso: string, todayIso: string): string {
  const days = epochDays(todayIso) - epochDays(activityIso);
  if (days === 0) return "hoje";
  if (days === 1) return "ontem";
  return `há ${days} dias`;
}

/** "08/11" — a data da prova no rótulo do chip. */
function dayMonth(iso: string): string {
  const [, month, day] = iso.split("-").map(Number);
  return `${String(day).padStart(2, "0")}/${String(month).padStart(2, "0")}`;
}

/** Um chip: rótulo caps em cima, valor embaixo — a anatomia do mock. */
function Chip({
  href,
  label,
  children,
}: {
  href: string;
  label: string;
  children: ReactNode;
}) {
  return (
    <Link
      href={href}
      className="flex min-h-11 flex-col justify-center rounded-ctl border border-border bg-card px-3 py-2.5 transition-colors hover:border-border-hover"
    >
      <span className="text-[9px] font-bold uppercase tracking-[0.11em] text-muted">
        {label}
      </span>
      <span className="mt-1 text-[12.5px] font-semibold tabular-nums">
        {children}
      </span>
    </Link>
  );
}

export default function RoutingChips({
  lastActivity,
  volume,
  countdown,
  date,
}: {
  lastActivity: HomeLastActivity | null;
  volume: HomeVolume | null;
  countdown: HomeCountdown | null;
  date: string;
}) {
  return (
    <div className="grid grid-cols-3 gap-2">
      {lastActivity !== null && (
        <Chip href={`/treinos/${lastActivity.id}`} label="Último treino">
          {formatKm(lastActivity.distance_m)} ·{" "}
          {relativeDate(lastActivity.date, date)}
          {lastActivity.evaluated && (
            <span className="text-accent"> · avaliado ✓</span>
          )}
        </Chip>
      )}
      {volume !== null && (
        <Chip href="/performance" label="Volume">
          {formatKm(volume.week_km * 1000)} ·{" "}
          {volume.delta_pct !== null ? (
            formatDeltaPct(volume.delta_pct)
          ) : (
            // Média de 4 semanas zerada -> "—", nunca % inventado (HOME-21)
            "—"
          )}
        </Chip>
      )}
      {countdown !== null && (
        <Chip
          href="/performance"
          label={`${countdown.name} · ${dayMonth(countdown.date)}`}
        >
          {countdown.days_left === 0
            ? "é hoje"
            : countdown.days_left === 1
              ? "falta 1 dia"
              : `faltam ${countdown.days_left} dias`}
        </Chip>
      )}
    </div>
  );
}
