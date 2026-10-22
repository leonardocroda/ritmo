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
  Cell,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { PmcBlock, PmcPoint } from "@/lib/api";
import { axisLine, chart, legendCaption, tick, tooltipCard } from "@/lib/chartTheme";
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

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-card border border-border bg-card px-2.5 py-2">
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
    <div className={tooltipCard}>
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
    { label: "CTL (fitness)", color: chart.subject },
    { label: "ATL (fadiga)", color: chart.alert },
    { label: "TSB (forma)", color: chart.context },
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
            <Tooltip content={<PmcTooltip />} />
            <ReferenceLine y={0} stroke={chart.context} strokeDasharray="4 4" />
            {/* TSB em contexto neutro; o dia atual (o mesmo dos cards de
                "Último dia") destacado em lime (DSN-13) */}
            <Bar dataKey="tsb" name="TSB" fill={chart.context} fillOpacity={0.45}>
              {points.map((point) => (
                <Cell
                  key={point.date}
                  fill={point.date === current.date ? chart.subject : chart.context}
                />
              ))}
            </Bar>
            <Line
              type="monotone"
              dataKey="ctl"
              name="CTL"
              stroke={chart.subject}
              strokeWidth={1.5}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="atl"
              name="ATL"
              stroke={chart.alert}
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
