"use client";

// Tendência do VO2max do relógio (POT-26) — Recharts LineChart (AD-008)
// com o selo "estimativa do relógio" e a nota de hierarquia de métricas
// (AD-005: provas/testes de campo > algoritmo) — a ressalva visual que o
// spec pede para não confundir estimativa com medição.

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { Vo2maxBlock } from "@/lib/api";
import { formatVdot } from "@/lib/format";

const AXIS_COLOR = "#3f3f46";
const MUTED_COLOR = "#a1a1aa";
const LINE_COLOR = "#a3e635"; // accent do tema

/** "2026-04-22" -> "22/04" (wall clock, sem conversão de fuso). */
function shortDay(date: string): string {
  const [, month, day] = date.split("-");
  return `${day}/${month}`;
}

function TrendTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: { date: string; value: number } }[];
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  const [year, month, day] = point.date.split("-");
  return (
    <div className="rounded-ctl border border-border bg-card px-3 py-2 text-xs">
      <p className="font-medium">
        VO2max {formatVdot(point.value)}
      </p>
      <p className="mt-0.5 text-muted">
        {day}/{month}/{year} · estimativa do relógio
      </p>
    </div>
  );
}

export default function Vo2maxTrend({ vo2max }: { vo2max: Vo2maxBlock }) {
  return (
    <div>
      <p className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-accent/15 px-2 py-0.5 text-sm font-medium text-accent">
          estimativa do relógio
        </span>
      </p>
      <div className="mt-3 h-52 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={vo2max.points}
            margin={{ top: 8, right: 12, bottom: 0, left: 0 }}
          >
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
              domain={["auto", "auto"]}
              width={38}
              stroke={AXIS_COLOR}
              tick={{ fill: MUTED_COLOR, fontSize: 10 }}
              tickLine={false}
            />
            <Tooltip content={<TrendTooltip />} />
            <Line
              type="monotone"
              dataKey="value"
              stroke={LINE_COLOR}
              strokeWidth={1.5}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-2 text-xs text-muted">
        Provas e testes de campo medem; o relógio estima a partir do ritmo e
        da FC — o algoritmo fica abaixo deles na hierarquia de métricas.
      </p>
    </div>
  );
}
