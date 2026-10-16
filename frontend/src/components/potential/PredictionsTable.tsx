// Tabela de previsões vs PRs (POT-21/22) — o coração anti-"precision
// theater" do painel (AD-004): as 4 estimativas lado a lado, "—" onde
// não há dado (nenhum número inventado) e a média honesta calculada só
// com as presentes (nota visível).

import type { CanonicalEvent, PredictionRow } from "@/lib/api";
import { formatDuration } from "@/lib/format";

// Rótulos PT-BR: ASCII na API, acento na exibição (padrão do tipo inferido)
const EVENT_LABELS: Record<CanonicalEvent, string> = {
  "5K": "5K",
  "10K": "10K",
  HALF_MARATHON: "Meia",
  MARATHON: "Maratona",
};

const EVENTS: CanonicalEvent[] = ["5K", "10K", "HALF_MARATHON", "MARATHON"];

/** "2026-04-26" -> "26/04/2026" (wall clock, sem conversão de fuso). */
function formatDay(date: string): string {
  const [year, month, day] = date.split("-");
  return `${day}/${month}/${year}`;
}

/** Tempo ou "—" — célula null nunca vira número (POT-22). */
function secondsOrDash(value: number | null): string {
  return value !== null ? formatDuration(value) : "—";
}

export default function PredictionsTable({
  predictions,
}: {
  predictions: Record<CanonicalEvent, PredictionRow>;
}) {
  return (
    <div>
      <div className="overflow-hidden rounded-xl border border-white/10 bg-card">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-[10px] text-muted">
              <th scope="col" className="px-2 py-2 font-normal">
                Distância
              </th>
              <th scope="col" className="px-1.5 py-2 font-normal">
                Garmin
              </th>
              <th scope="col" className="px-1.5 py-2 font-normal">
                Riegel
              </th>
              <th scope="col" className="px-1.5 py-2 font-normal">
                VDOT
              </th>
              <th scope="col" className="px-1.5 py-2 font-normal">
                Média
              </th>
              <th scope="col" className="px-2 py-2 text-right font-normal">
                PR
              </th>
            </tr>
          </thead>
          <tbody>
            {EVENTS.map((event) => {
              const row = predictions[event];
              return (
                <tr key={event} className="border-t border-white/10">
                  <th
                    scope="row"
                    className="px-2 py-2 text-left font-medium whitespace-nowrap"
                  >
                    {EVENT_LABELS[event]}
                  </th>
                  <td className="px-1.5 py-2">{secondsOrDash(row.garmin_s)}</td>
                  <td className="px-1.5 py-2">{secondsOrDash(row.riegel_s)}</td>
                  <td className="px-1.5 py-2">{secondsOrDash(row.vdot_s)}</td>
                  <td className="px-1.5 py-2">{secondsOrDash(row.average_s)}</td>
                  <td className="px-2 py-2 text-right">
                    {row.pr_s !== null ? (
                      <span className="inline-block leading-tight">
                        {formatDuration(row.pr_s)}
                        {row.pr_date !== null && (
                          <span className="block text-[10px] text-muted">
                            {formatDay(row.pr_date)}
                          </span>
                        )}
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs text-muted">
        A média honesta calcula só as estimativas presentes na distância —
        nenhuma célula é inventada.
      </p>
    </div>
  );
}
