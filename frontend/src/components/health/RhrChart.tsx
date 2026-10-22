"use client";

// RHR vs baseline da janela (HLT-18) — Recharts ComposedChart (AD-008,
// padrão PmcChart): linha dos valores + ReferenceLine tracejada no
// baseline do payload (média da janela, régua do backend) rotulada.

import {
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { RhrBlock, RhrPoint } from "@/lib/api";
import { formatVdot } from "@/lib/format";

const AXIS_COLOR = "#3f3f46";
const MUTED_COLOR = "#a1a1aa";
const RHR_COLOR = "#f87171"; // FC de repouso (mesma cor de fadiga do PMC)
const BASELINE_COLOR = MUTED_COLOR; // baseline — linha neutra tracejada

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

function RhrTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: RhrPoint }[];
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className="rounded-xl border border-border bg-card px-3 py-2 text-xs">
      <p className="font-medium">{fullDay(point.date)}</p>
      <p className="mt-1 text-muted">RHR {point.value} bpm</p>
    </div>
  );
}

export default function RhrChart({ rhr }: { rhr: RhrBlock }) {
  const { points, baseline } = rhr;

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
            <YAxis
              width={38}
              stroke={AXIS_COLOR}
              tick={{ fill: MUTED_COLOR, fontSize: 10 }}
              tickLine={false}
            />
            <Tooltip content={<RhrTooltip />} />
            {/* Baseline = média da janela (dentro do intervalo dos dados) */}
            <ReferenceLine
              y={baseline}
              stroke={BASELINE_COLOR}
              strokeDasharray="4 4"
              label={{
                value: `baseline ${formatVdot(baseline)}`,
                position: "insideTopRight",
                fill: BASELINE_COLOR,
                fontSize: 10,
              }}
            />
            <Line
              type="monotone"
              dataKey="value"
              name="RHR"
              stroke={RHR_COLOR}
              strokeWidth={1.5}
              dot={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
