"use client";

// Tendência de HRV noturna (HLT-17) — Recharts ComposedChart (AD-008,
// padrão PmcChart): linha dos valores da janela + valor atual em destaque
// com o status do último dia como badge textual. O status cru da API
// (BALANCED/UNBALANCED/LOW) é exibido como vem — sem tradução inventada.

import {
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { HrvBlock, HrvPoint } from "@/lib/api";
import { formatVdot } from "@/lib/format";

const AXIS_COLOR = "#3f3f46";
const MUTED_COLOR = "#a1a1aa";
const HRV_COLOR = "#38bdf8"; // linha de HRV (mesma cor de fitness do PMC)

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

/** Status cru da noite ou "—" (null atravessa o contrato). */
function statusLabel(status: string | null): string {
  return status ?? "—";
}

function HrvTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: HrvPoint }[];
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className="rounded-xl border border-white/10 bg-card px-3 py-2 text-xs">
      <p className="font-medium">{fullDay(point.date)}</p>
      <p className="mt-1 text-muted">
        HRV {formatVdot(point.value)} · {statusLabel(point.status)}
      </p>
    </div>
  );
}

export default function HrvChart({ hrv }: { hrv: HrvBlock }) {
  const { points, current } = hrv;

  return (
    <div>
      <p className="text-xs text-muted">Último dia</p>
      <p className="mt-1 flex items-baseline gap-2">
        <span className="text-3xl font-semibold tracking-tight tabular-nums">
          {formatVdot(current.value)}
        </span>
        {/* Badge textual: status cru da API, sem tradução (HLT-17) */}
        <span className="rounded-full border border-white/10 bg-card px-2 py-0.5 text-xs text-muted">
          {statusLabel(current.status)}
        </span>
      </p>

      <div className="mt-3 h-56 w-full">
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
              tickFormatter={(value: number) => String(value)}
            />
            <Tooltip content={<HrvTooltip />} />
            <Line
              type="monotone"
              dataKey="value"
              name="HRV"
              stroke={HRV_COLOR}
              strokeWidth={1.5}
              dot={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
