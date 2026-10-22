"use client";

// Duração de sono por noite vs piso (HLT-13/14) — Recharts ComposedChart
// (AD-008, padrão PmcChart): barras de duração em horas, linha tracejada no
// floor_s do payload (régua do backend, não inventada na UI) e resumo
// "% das noites abaixo do piso" acima do gráfico. Tooltip com score e REM%.

import {
  Bar,
  ComposedChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { SleepBlock, SleepPoint } from "@/lib/api";
import { axisLine, chart, legendCaption, tick, tooltipCard } from "@/lib/chartTheme";
import { formatHours, formatVdot } from "@/lib/format";

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

/** Ponto em horas para as barras (o payload traz segundos). */
type SleepBar = SleepPoint & { hours: number };

/** Tick do eixo Y em horas — vírgula PT-BR só quando fracionário. */
function hourTick(hours: number): string {
  return Number.isInteger(hours) ? String(hours) : formatVdot(hours);
}

/** REM% ou "—" (null atravessa o contrato). */
function remLabel(remPct: number | null): string {
  return remPct !== null ? `${formatVdot(remPct)}%` : "—";
}

function SleepTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: SleepBar }[];
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className={tooltipCard}>
      <p className="font-medium">{fullDay(point.date)}</p>
      <p className="mt-1 text-muted">{formatHours(point.duration_s)}</p>
      <p className="mt-0.5 text-muted">
        Score {point.score ?? "—"} · REM {remLabel(point.rem_pct)}
      </p>
    </div>
  );
}

function SeriesLegend({ floorS }: { floorS: number }) {
  const series = [
    { label: "duração", color: chart.subject },
    { label: `piso (${formatHours(floorS)})`, color: chart.context },
  ];
  return (
    <div className={legendCaption}>
      {series.map((item) => (
        <span key={item.label} className="flex items-center gap-1.5">
          <span
            aria-hidden
            className="inline-block h-2.5 w-2.5 rounded-sm"
            style={{ backgroundColor: item.color }}
          />
          {item.label}
        </span>
      ))}
    </div>
  );
}

export default function SleepChart({ sleep }: { sleep: SleepBlock }) {
  const { points, floor_s, below_floor } = sleep;
  const bars: SleepBar[] = points.map((point) => ({
    ...point,
    hours: point.duration_s / 3600,
  }));
  const floorHours = floor_s / 3600;

  return (
    <div>
      {/* Resumo HLT-14: pct com 1 casa vem do backend (below_floor) */}
      <p className="text-xs text-muted">
        <span className="font-medium tabular-nums">
          {below_floor.pct.toFixed(1).replace(".", ",")}%
        </span>{" "}
        das noites abaixo do piso
      </p>

      <div className="mt-3 h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={bars} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
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
              tickFormatter={hourTick}
            />
            <Tooltip content={<SleepTooltip />} />
            {/* extendDomain: o piso fica visível mesmo se TODAS as noites
                estiverem abaixo dele (domínio estica até a régua) */}
            <ReferenceLine
              y={floorHours}
              stroke={chart.context}
              strokeDasharray="4 4"
              ifOverflow="extendDomain"
            />
            <Bar dataKey="hours" name="duração" fill={chart.subject} fillOpacity={0.8} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <SeriesLegend floorS={floor_s} />
    </div>
  );
}
