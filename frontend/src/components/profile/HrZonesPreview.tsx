"use client";

// Preview das zonas resultantes em bpm (feature hr-zones —
// HRZ-10/11/13): render das `zones` do estado da página — a resposta
// do GET/PUT — então "salvar → zonas mudam na hora" (HRZ-14). Null é
// estado vazio honesto (HRZ-11): sem config orienta escolher o
// método; com config mas sem a métrica exigida orienta preencher o
// valor faltante na seção 1 — nunca erro.

import type { ReactNode } from "react";

import type {
  HrZone,
  HrZoneConfig,
  HrZoneMethod,
  HrZonesOut,
} from "@/lib/api";

type MetricKind = keyof HrZonesOut["metrics"];

// Métricas que cada método exige (calc.zones_bpm) — para apontar o
// valor faltante quando as zonas vêm null.
const REQUIRED_METRICS: Record<HrZoneMethod, { kind: MetricKind; label: string }[]> = {
  lthr: [{ kind: "fclthr", label: "LTHR" }],
  fcr: [
    { kind: "fcrest", label: "FC de repouso" },
    { kind: "fcmax", label: "FC máxima" },
  ],
  fcmax: [{ kind: "fcmax", label: "FC máxima" }],
};

function EmptyState({ children }: { children: ReactNode }) {
  return (
    <p className="rounded-xl border border-border bg-card px-4 py-3 text-sm text-muted">
      {children}
    </p>
  );
}

export default function HrZonesPreview({
  zones,
  config,
  metrics,
}: {
  zones: HrZone[] | null;
  config: HrZoneConfig | null;
  metrics: HrZonesOut["metrics"];
}) {
  if (zones === null) {
    if (config === null) {
      return (
        <EmptyState>
          Nenhum método configurado — escolha um método acima e salve para
          gerar as zonas.
        </EmptyState>
      );
    }
    const missing = REQUIRED_METRICS[config.method].filter(
      (metric) => metrics[metric.kind] === null,
    );
    if (missing.length > 0) {
      const labels = missing.map((metric) => metric.label).join(" e ");
      return (
        <EmptyState>
          {missing.length > 1 ? "Faltam" : "Falta"} {labels} — as zonas em bpm
          aparecem quando o valor estiver configurado (seção 1).
        </EmptyState>
      );
    }
    return (
      <EmptyState>Sem zonas para o método escolhido.</EmptyState>
    );
  }

  return (
    <div className="rounded-xl border border-border bg-card px-3 py-2">
      <p className="text-xs text-muted">Zonas resultantes (bpm)</p>
      <ul className="mt-1 space-y-1">
        {zones.map((zone) => (
          <li
            key={zone.n}
            className="flex items-baseline justify-between gap-2 text-sm tabular-nums"
          >
            <span className="text-muted">Z{zone.n}</span>
            <span>
              {zone.low}
              {zone.high === null ? "+" : `–${zone.high}`} bpm
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
