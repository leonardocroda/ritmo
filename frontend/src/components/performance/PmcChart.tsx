"use client";

// Curva PMC fitness/fadiga — seção Carga de treino do painel
// Performance (AD-017 reverte a CLR-03; CLR-07/08 do panel-clarity) —
// Recharts ComposedChart (AD-008): TSB como barras
// semitransparentes atrás, CTL e ATL como linhas, zero marcado. Cards
// do último dia com ACWR "—" quando null (CLR-10 — janela de 28d
// incompleta, honestidade do SYNC-24, nenhum número inventado).
// POT-23/24 (potential-panel) voltam a valer — a curva mora no painel
// de novo.

import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { PmcBlock, PmcPoint } from "@/lib/api";
import { formatVdot } from "@/lib/format";

const AXIS_COLOR = "#3f3f46";
const MUTED_COLOR = "#a1a1aa";
const CTL_COLOR = "#38bdf8"; // fitness
const ATL_COLOR = "#f87171"; // fadiga
const TSB_COLOR = "#a3e635"; // forma (accent do tema)

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

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-card px-2.5 py-2">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="mt-0.5 text-sm font-medium tabular-nums">{value}</dd>
    </div>
  );
}

/** Valor com 1 casa ou "—" (null do banco atravessa o contrato). */
function statOrDash(value: number | null): string {
  return value !== null ? formatVdot(value) : "—";
}

function PmcTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: PmcPoint }[];
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className="rounded-xl border border-white/10 bg-card px-3 py-2 text-xs">
      <p className="font-medium">{fullDay(point.date)}</p>
      <p className="mt-1 text-muted">
        CTL {statOrDash(point.ctl)} · ATL {statOrDash(point.atl)}
      </p>
      <p className="mt-0.5 text-muted">
        TSB {statOrDash(point.tsb)} · ACWR {statOrDash(point.acwr)}
      </p>
    </div>
  );
}

function SeriesLegend() {
  const series = [
    { label: "CTL (fitness)", color: CTL_COLOR },
    { label: "ATL (fadiga)", color: ATL_COLOR },
    { label: "TSB (forma)", color: TSB_COLOR },
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

export default function PmcChart({ pmc }: { pmc: PmcBlock }) {
  const { points, current } = pmc;

  return (
    <div>
      <p className="text-xs text-muted">Último dia</p>
      <dl className="mt-1.5 grid grid-cols-4 gap-2">
        <StatCard label="CTL" value={statOrDash(current.ctl)} />
        <StatCard label="ATL" value={statOrDash(current.atl)} />
        <StatCard label="TSB" value={statOrDash(current.tsb)} />
        {/* ACWR null = janela de 28d incompleta — "—" (SYNC-24) */}
        <StatCard label="ACWR" value={statOrDash(current.acwr)} />
      </dl>

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
            />
            <Tooltip content={<PmcTooltip />} />
            <ReferenceLine y={0} stroke={MUTED_COLOR} strokeDasharray="4 4" />
            <Bar dataKey="tsb" name="TSB" fill={TSB_COLOR} fillOpacity={0.45} />
            <Line
              type="monotone"
              dataKey="ctl"
              name="CTL"
              stroke={CTL_COLOR}
              strokeWidth={1.5}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="atl"
              name="ATL"
              stroke={ATL_COLOR}
              strokeWidth={1.5}
              dot={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <SeriesLegend />
    </div>
  );
}
