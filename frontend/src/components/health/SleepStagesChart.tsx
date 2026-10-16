"use client";

// Composição de fases por noite (HLT-30) — Recharts BarChart empilhado
// (AD-008, padrão PmcChart): leve (base, neutra) + profundo + REM com um
// stackId só e domínio Y 0–100. Os pcts passam como gravados — sem
// normalização (a série real soma 100,0–100,2%; edge do spec). Tooltip
// com as 3 fases e o número de despertares (omitido quando null).

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { SleepBlock, SleepPoint } from "@/lib/api";
import { formatVdot } from "@/lib/format";

const AXIS_COLOR = "#3f3f46";
const MUTED_COLOR = "#a1a1aa";
const LIGHT_COLOR = "#a1a1aa"; // fase leve — base neutra
const DEEP_COLOR = "#38bdf8"; // fase profunda
const REM_COLOR = "#a3e635"; // REM (accent do tema)

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

/** Fase em % com vírgula PT-BR ou "—" (null atravessa o contrato). */
function pctLabel(value: number | null): string {
  return value !== null ? `${formatVdot(value)}%` : "—";
}

/** "2 despertares" / "1 despertar" — plural é camada de exibição. */
function awakeningsLabel(awakenings: number): string {
  return awakenings === 1 ? "1 despertar" : `${awakenings} despertares`;
}

function StagesTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: SleepPoint }[];
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className="rounded-xl border border-white/10 bg-card px-3 py-2 text-xs">
      <p className="font-medium">{fullDay(point.date)}</p>
      <p className="mt-1 text-muted">
        Leve {pctLabel(point.light_pct)} · Profundo {pctLabel(point.deep_pct)} · REM{" "}
        {pctLabel(point.rem_pct)}
      </p>
      {/* Noite sem contagem de despertares: linha omitida, nada inventado */}
      {point.awakenings !== null && (
        <p className="mt-0.5 text-muted">{awakeningsLabel(point.awakenings)}</p>
      )}
    </div>
  );
}

function SeriesLegend() {
  const series = [
    { label: "leve", color: LIGHT_COLOR },
    { label: "profundo", color: DEEP_COLOR },
    { label: "REM", color: REM_COLOR },
  ];
  return (
    <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
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

export default function SleepStagesChart({ sleep }: { sleep: SleepBlock }) {
  return (
    <div>
      <div className="h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={sleep.points} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid stroke={AXIS_COLOR} strokeOpacity={0.35} />
            <XAxis
              dataKey="date"
              tickFormatter={shortDay}
              minTickGap={28}
              stroke={AXIS_COLOR}
              tick={{ fill: MUTED_COLOR, fontSize: 10 }}
              tickLine={false}
            />
            <YAxis
              width={38}
              domain={[0, 100]}
              stroke={AXIS_COLOR}
              tick={{ fill: MUTED_COLOR, fontSize: 10 }}
              tickLine={false}
            />
            <Tooltip content={<StagesTooltip />} />
            {/* stackId único: leve na base, profundo e REM por cima —
                os pcts entram como gravados (sem normalização) */}
            <Bar dataKey="light_pct" name="leve" stackId="fases" fill={LIGHT_COLOR} fillOpacity={0.45} />
            <Bar dataKey="deep_pct" name="profundo" stackId="fases" fill={DEEP_COLOR} />
            <Bar dataKey="rem_pct" name="REM" stackId="fases" fill={REM_COLOR} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <SeriesLegend />
    </div>
  );
}
