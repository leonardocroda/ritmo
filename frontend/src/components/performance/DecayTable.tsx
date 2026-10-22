// Tabela de decaimento por distância (POT-28/29) — pace real (PR) vs
// ideal (equivalência do VDOT corrente) e Δ% com sinal; o maior gap (o
// delta mais negativo) é destacado. Explicação sempre visível do que
// compara e do sinal (CLR-20) — método explicado, número sem
// interpretação inventada e sem gráfico dedicado (§9.1).

import type { CanonicalEvent, DecayRow } from "@/lib/api";
import { formatPace } from "@/lib/format";

// Rótulos PT-BR (mesmo padrão da tabela de previsões)
const EVENT_LABELS: Record<CanonicalEvent, string> = {
  "5K": "5K",
  "10K": "10K",
  HALF_MARATHON: "Meia",
  MARATHON: "Maratona",
};

/** Δ% com sinal e vírgula: -22.1 -> "-22,1%"; 2.3 -> "+2,3%". */
function formatDelta(deltaPct: number): string {
  const fixed = deltaPct.toFixed(1).replace(".", ",");
  return `${deltaPct > 0 ? "+" : ""}${fixed}%`;
}

export default function DecayTable({ rows }: { rows: DecayRow[] }) {
  if (rows.length === 0) return null;

  // Maior gap = delta mais negativo (identidade do objeto para destacar 1 linha)
  const worstGap = rows.reduce((worst, row) =>
    row.delta_pct < worst.delta_pct ? row : worst,
  );

  return (
    <div>
      <div className="overflow-hidden rounded-xl border border-border bg-card">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-muted">
              <th scope="col" className="px-4 py-2 font-normal">
                Distância
              </th>
              <th scope="col" className="px-3 py-2 font-normal">
                Real (PR)
              </th>
              <th scope="col" className="px-3 py-2 font-normal">
                Ideal (VDOT)
              </th>
              <th scope="col" className="px-4 py-2 text-right font-normal">
                Δ%
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.event}
                className={
                  row === worstGap
                    ? "border-t border-border bg-accent/10"
                    : "border-t border-border"
                }
              >
                <th
                  scope="row"
                  className="px-4 py-2 text-left font-medium whitespace-nowrap"
                >
                  {EVENT_LABELS[row.event]}
                </th>
                <td className="px-3 py-2 whitespace-nowrap">
                  {formatPace(row.real_pace_s)}/km
                </td>
                <td className="px-3 py-2 whitespace-nowrap">
                  {formatPace(row.ideal_pace_s)}/km
                </td>
                <td
                  className={`px-4 py-2 text-right tabular-nums ${
                    row === worstGap ? "font-medium text-accent" : ""
                  }`}
                >
                  {formatDelta(row.delta_pct)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs text-muted">
        Compara o pace real dos seus PRs com o pace ideal da equivalência
        VDOT do teste corrente. Negativo = pace real mais lento que o
        ideal — gap de execução/especificidade, não de motor.
      </p>
    </div>
  );
}
