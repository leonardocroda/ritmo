"use client";

// Digest de previsões (mock v0.3 §03, fpanel "Previsões de prova") — a
// linha 10K · meia com os tempos médios do payload (HOME-38) e o link
// para o painel Performance: a Home roteia, nunca duplica painel. O
// bloco só existe com predições (null = omitido — a Home nunca 500 por
// bloco P2); evento sem predição já não chega (o backend omite, HOME-39).

import Link from "next/link";

import type { HomePrediction } from "@/lib/api";
import { formatDuration } from "@/lib/format";

/** Rótulo exibível do evento: 10K fica 10K, HALF_MARATHON vira "meia"
 * (mock "10K 41:15 · meia 1:29:2x" — sentence case, nunca o enum cru). */
function eventLabel(event: string): string {
  return event === "HALF_MARATHON" ? "meia" : event;
}

export default function PredictionsDigest({
  predictions,
}: {
  predictions: HomePrediction[];
}) {
  const line = predictions
    .map((prediction) => `${eventLabel(prediction.event)} ${formatDuration(prediction.time_s)}`)
    .join(" · ");

  return (
    <div className="rounded-card border border-border bg-card p-4">
      <p className="text-[9.5px] font-bold uppercase tracking-[0.11em] text-muted">
        Previsões de prova
      </p>
      <div className="mt-1 flex items-center justify-between gap-2.5">
        <p className="text-[15px] font-semibold tabular-nums">{line}</p>
        <Link
          href="/performance"
          className="inline-flex min-h-11 items-center whitespace-nowrap text-[11.5px] text-muted transition-colors hover:text-foreground"
        >
          ver Performance →
        </Link>
      </div>
    </div>
  );
}
