"use client";

// Dose-resposta (HLT-20/21/22) — o comparativo que convence a dormir
// (§4.5): dois cards lado a lado (<6h vs ≥6h45) com noites, HRV média e
// score médio da mesma noite, mais a nota da faixa neutra. Média null
// (bucket vazio) -> "—" — nenhum número inventado.

import type { DoseBucket, DoseResponse as DoseResponseData } from "@/lib/api";

/** Média com 1 casa e vírgula PT-BR (padrão format.ts): 69.5 -> "69,5". */
function formatAvg(value: number): string {
  return value.toFixed(1).replace(".", ",");
}

/** Média ou "—" (bucket sem noites não inventa número). */
function avgOrDash(value: number | null): string {
  return value !== null ? formatAvg(value) : "—";
}

/** Contagem com plural PT-BR: 1 noite / 17 noites. */
function nights(n: number): string {
  return `${n} ${n === 1 ? "noite" : "noites"}`;
}

function DoseCard({ label, bucket }: { label: string; bucket: DoseBucket }) {
  return (
    <div className="rounded-xl border border-white/10 bg-card px-3 py-2">
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-0.5 text-sm font-medium tabular-nums">{nights(bucket.nights)}</p>
      <dl className="mt-1.5 space-y-1 text-xs">
        <div className="flex items-baseline justify-between gap-2">
          <dt className="text-muted">HRV média</dt>
          <dd className="tabular-nums">{avgOrDash(bucket.avg_hrv)}</dd>
        </div>
        <div className="flex items-baseline justify-between gap-2">
          <dt className="text-muted">Score médio</dt>
          <dd className="tabular-nums">{avgOrDash(bucket.avg_score)}</dd>
        </div>
      </dl>
    </div>
  );
}

export default function DoseResponse({ dose }: { dose: DoseResponseData }) {
  return (
    <div>
      <div className="grid grid-cols-2 gap-2">
        <DoseCard label="Noites <6h" bucket={dose.short} />
        <DoseCard label="Noites ≥6h45" bucket={dose.adequate} />
      </div>
      <p className="mt-2 text-xs text-muted">
        {nights(dose.neutral_nights)} fora da comparação (6h–6h45)
      </p>
    </div>
  );
}
