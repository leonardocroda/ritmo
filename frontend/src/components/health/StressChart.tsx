"use client";

// Estresse médio diário (HLT-25/26) — Recharts ComposedChart (AD-008,
// padrão PmcChart): linha da média por dia + média da janela em card.
// Bloco stress null (série vazia) -> card "—" e nenhuma linha — nenhum
// número inventado (HLT-26); o card fica de pé sem quebrar o bloco.

import {
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { StressBlock, StressPoint } from "@/lib/api";
import { axisLine, chart, tick, tooltipCard } from "@/lib/chartTheme";
import { formatVdot } from "@/lib/format";

/** "2026-04-20" -> "20/04" (wall clock, sem conversão de fuso). */
function shortDay(date: string): string {
  const [, month, day] = date.split("-");
  return `${day}/${month}`;
}

/** "2026-04-20" -> "20/04/2026". */
function fullDay(date: string): string {
  const [year, month, day] = date.split("-");
  return `${day}/${month}/${year}`;
}

function StressTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: StressPoint }[];
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className={tooltipCard}>
      <p className="font-medium">{fullDay(point.date)}</p>
      <p className="mt-1 text-muted">Estresse {point.avg}</p>
    </div>
  );
}

export default function StressChart({ stress }: { stress: StressBlock | null }) {
  return (
    <div>
      <p className="text-xs text-muted">Média da janela</p>
      <p className="mt-0.5 text-3xl font-semibold tracking-tight tabular-nums">
        {stress !== null ? formatVdot(stress.avg_window) : "—"}
      </p>

      {stress !== null && (
        <div className="mt-3 h-56 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={stress.points} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
              <XAxis
                dataKey="date"
                tickFormatter={shortDay}
                minTickGap={28}
                axisLine={axisLine}
                tick={tick}
                tickLine={false}
              />
              <YAxis
                width={38}
                axisLine={false}
                tick={tick}
                tickLine={false}
              />
              <Tooltip content={<StressTooltip />} />
              <Line
                type="monotone"
                dataKey="avg"
                name="estresse"
                stroke={chart.alert}
                strokeWidth={1.5}
                dot={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
