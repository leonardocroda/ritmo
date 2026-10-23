"use client";

// Card de exibição da conexão Garmin (feature garmin-tokens-db —
// GTDB-16): pill por estado + "tokens atualizados em …" quando existir.
// SÓ exibição — o re-login é CLI do operador (decisão do spec: /perfil
// não tem botão de ação). As pills seguem o padrão visual dos cards do
// perfil (bg-accent/15) com o vermelho dos erros para reautenticação.

import type { GarminConnectionOut } from "@/lib/api";

type ConnectionState = GarminConnectionOut["state"];

const STATE_META: Record<ConnectionState, { label: string; pill: string }> = {
  connected: {
    label: "Conectado",
    pill: "rounded-full bg-accent/15 px-2 py-0.5 text-xs font-medium text-accent",
  },
  reauth_needed: {
    label: "Reautenticação necessária",
    pill: "rounded-full bg-red-400/15 px-2 py-0.5 text-xs font-medium text-red-400",
  },
  not_connected: {
    label: "Não conectado",
    pill: "rounded-full bg-white/10 px-2 py-0.5 text-xs font-medium text-muted",
  },
};

/** ISO do backend ("2026-10-22T10:00:00") → "22/10/2026" — mesmo
 * formato de data do resto do perfil (wall clock, sem fuso). */
function formatDate(iso: string): string {
  return iso.split("T")[0].split("-").reverse().join("/");
}

export default function ConnectionCard({
  state,
  tokensUpdatedAt,
}: {
  state: ConnectionState;
  tokensUpdatedAt: string | null;
}) {
  const meta = STATE_META[state];
  return (
    <div className="rounded-xl border border-white/10 bg-card px-4 py-3">
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
        <span className={meta.pill}>{meta.label}</span>
        {tokensUpdatedAt !== null && (
          <span className="text-xs text-muted tabular-nums">
            tokens atualizados em {formatDate(tokensUpdatedAt)}
          </span>
        )}
      </div>
    </div>
  );
}
