"use client";

// REM% por noite com a banda ideal (HLT-15) — Recharts ComposedChart
// (AD-008, padrão PmcChart): linha de rem_pct + ReferenceArea da banda
// rem_band do payload (21–31, régua do backend — a UI não inventa régua)
// e domínio Y 0–40 fixo, para a média real (~14%) não colapsar na base.

import {
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { SleepBlock, SleepPoint } from "@/lib/api";
import { formatVdot } from "@/lib/format";

const AXIS_COLOR = "#3f3f46";
const MUTED_COLOR = "#a1a1aa";
const REM_COLOR = "#a3e635"; // linha de REM (accent do tema)
const BAND_COLOR = "#a3e635"; // banda ideal — mesma série, fundo suave

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

function RemTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: SleepPoint }[];
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className="rounded-ctl border border-border bg-card px-3 py-2 text-xs">
      <p className="font-medium">{fullDay(point.date)}</p>
      <p className="mt-1 text-muted">
        REM {point.rem_pct !== null ? `${formatVdot(point.rem_pct)}%` : "—"}
      </p>
    </div>
  );
}

function SeriesLegend({ band }: { band: number[] }) {
  const [low, high] = band;
  const series = [
    { label: "REM %", color: REM_COLOR },
    {
      label: `banda ideal (${formatVdot(low)}–${formatVdot(high)}%)`,
      color: BAND_COLOR,
    },
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

export default function RemChart({ sleep }: { sleep: SleepBlock }) {
  const { points, rem_band } = sleep;
  const [bandLow, bandHigh] = rem_band;

  return (
    <div>
      <div className="h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={points} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid stroke={AXIS_COLOR} strokeOpacity={0.35} />
            <XAxis
              dataKey="date"
              tickFormatter={shortDay}
              minTickGap={28}
              stroke={AXIS_COLOR}
              tick={{ fill: MUTED_COLOR, fontSize: 10 }}
              tickLine={false}
            />
            {/* Domínio 0–40 fixo: banda 21–31 e média ~14% na mesma escala */}
            <YAxis
              width={38}
              domain={[0, 40]}
              stroke={AXIS_COLOR}
              tick={{ fill: MUTED_COLOR, fontSize: 10 }}
              tickLine={false}
            />
            <Tooltip content={<RemTooltip />} />
            <ReferenceArea
              y1={bandLow}
              y2={bandHigh}
              fill={BAND_COLOR}
              fillOpacity={0.15}
            />
            <Line
              type="monotone"
              dataKey="rem_pct"
              name="REM %"
              stroke={REM_COLOR}
              strokeWidth={1.5}
              dot={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <SeriesLegend band={rem_band} />
    </div>
  );
}
