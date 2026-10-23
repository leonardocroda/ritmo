"use client";

// Seção 3 "Histórico" (feature hr-zones — HRZ-15): timeline das
// mudanças de métricas e configs vindas do
// getHrZonesHistory — as duas séries já chegam DESC por
// (valid_from, id); aqui elas são fundidas em uma única timeline,
// mais recente primeiro (datas ISO ordenam lexicograficamente e o
// sort é estável — dentro de cada série o tie-break do backend é
// preservado). Métricas mostram data, valor e badge de fonte
// (Garmin/Manual); configs mostram data, método e os cortes — configs
// não têm fonte no contrato. Vazio é honesto: nenhuma mudança
// registrada ainda.

import type { HrMetricHistory, HrConfigHistory } from "@/lib/api";

const METRIC_LABELS: Record<HrMetricHistory["kind"], string> = {
  fcmax: "FC máxima",
  fcrest: "FC de repouso",
  fclthr: "LTHR",
};

const METHOD_LABELS: Record<HrConfigHistory["method"], string> = {
  lthr: "LTHR%",
  fcr: "reserva cardíaca",
  fcmax: "FC máx%",
};

type Entry =
  | { type: "metric"; date: string; text: string; source: string }
  | { type: "config"; date: string; text: string };

/** "garmin" → "Garmin" — a API manda ASCII, a UI rotula. */
function sourceLabel(source: string): string {
  return source === "garmin" ? "Garmin" : "Manual";
}

/** valid_from ISO "2026-10-20" → "20/10/2026" (wall clock, sem fuso). */
function formatDate(iso: string): string {
  return iso.split("-").reverse().join("/");
}

export default function HrHistoryList({
  history,
}: {
  history: { metrics: HrMetricHistory[]; configs: HrConfigHistory[] };
}) {
  const entries: Entry[] = [
    ...history.metrics.map((metric) => ({
      type: "metric" as const,
      date: metric.valid_from,
      text: `${METRIC_LABELS[metric.kind]} ${metric.value} bpm`,
      source: metric.source,
    })),
    ...history.configs.map((config) => ({
      type: "config" as const,
      date: config.valid_from,
      text: `Método ${METHOD_LABELS[config.method]} · cortes ${config.bounds.zones
        .map((zone) => zone.low)
        .join("/")}`,
    })),
  ].sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));

  if (entries.length === 0) {
    return (
      <p className="rounded-card border border-border bg-card px-4 py-3 text-sm text-muted">
        Nenhuma mudança registrada ainda — edite valores ou método e elas
        aparecem aqui.
      </p>
    );
  }

  return (
    <ol className="space-y-1">
      {entries.map((entry, i) => (
        <li
          key={i}
          className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5 text-sm"
        >
          <span className="text-xs text-muted tabular-nums">
            {formatDate(entry.date)}
          </span>
          <span className="tabular-nums">{entry.text}</span>
          {entry.type === "metric" && (
            <span className="rounded-full bg-accent/15 px-2 py-0.5 text-xs font-medium text-accent">
              {sourceLabel(entry.source)}
            </span>
          )}
        </li>
      ))}
    </ol>
  );
}
