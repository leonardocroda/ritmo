"use client";

// HRV no modelo científico (hrv-baseline, HRV-01..HRV-13) — Recharts
// ComposedChart (AD-008, padrão PmcChart): pontos das noites individuais
// (Scatter), linha da média móvel de 7 dias e banda normal por dia (2
// Areas empilhadas — ReferenceArea não tem limites por ponto; dias sem
// banda quebram a área). O status do card é o local do payload (média 7d
// vs banda, calculada no backend); o status cru da Garmin saiu da UI do
// Saúde (decisão da spec).

import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ScatterShapeProps } from "recharts";

import type { HrvBlock, HrvPoint } from "@/lib/api";
import { formatVdot } from "@/lib/format";

const AXIS_COLOR = "#3f3f46";
const MUTED_COLOR = "#a1a1aa";
const HRV_COLOR = "#38bdf8"; // HRV (mesma cor de fitness do PMC)
const BAND_OPACITY = 0.12; // banda normal — fundo suave (padrão RemChart)
const OUT_COLOR = "#fbbf24"; // noite fora da banda (HRV-13)

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

function formatMs(value: number | null): string {
  return value == null ? "—" : `${formatVdot(value)} ms`;
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
    <div className="rounded-xl border border-border bg-card px-3 py-2 text-xs">
      <p className="font-medium">{fullDay(point.date)}</p>
      <p className="mt-1 text-muted">
        {point.value != null ? `HRV ${formatVdot(point.value)} ms` : "sem captura"} ·
        média 7d {formatMs(point.avg7)}
      </p>
      {point.band_low != null && point.band_high != null && (
        <p className="mt-0.5 text-muted">
          banda {formatVdot(point.band_low)}–{formatVdot(point.band_high)} ms
        </p>
      )}
    </div>
  );
}

/** Noite individual como ponto discreto; fora da banda em âmbar (HRV-13). */
function NightDot(props: ScatterShapeProps) {
  const point = props.payload as HrvPoint | undefined;
  if (props.cx == null || props.cy == null || !point || point.value == null) {
    return null;
  }
  const out =
    point.band_low != null &&
    point.band_high != null &&
    (point.value < point.band_low || point.value > point.band_high);
  return (
    <circle
      cx={props.cx}
      cy={props.cy}
      r={2}
      fill={out ? OUT_COLOR : HRV_COLOR}
      fillOpacity={0.8}
    />
  );
}

function SeriesLegend() {
  const series = [
    { label: "noite", color: HRV_COLOR, opacity: 0.8 },
    { label: "noite fora da banda", color: OUT_COLOR, opacity: 0.8 },
    { label: "média 7 dias", color: HRV_COLOR, opacity: 1 },
    { label: "banda normal", color: HRV_COLOR, opacity: BAND_OPACITY },
  ];
  return (
    <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
      {series.map((item) => (
        <span key={item.label} className="flex items-center gap-1.5">
          <span
            aria-hidden
            className="inline-block h-2.5 w-2.5 rounded-full"
            style={{ backgroundColor: item.color, opacity: item.opacity }}
          />
          {item.label}
        </span>
      ))}
    </div>
  );
}

export default function HrvChart({ hrv }: { hrv: HrvBlock }) {
  const { points, current } = hrv;

  // Campos derivados de render: a banda empilhada precisa de base+altura
  // (base transparente + span preenchida = banda entre low e high).
  const data = points.map((p) => ({
    ...p,
    bandBase: p.band_low,
    bandSpan:
      p.band_low != null && p.band_high != null ? p.band_high - p.band_low : null,
  }));

  return (
    <div>
      <p className="text-xs text-muted">Média 7 dias</p>
      <p className="mt-1 flex items-baseline gap-2">
        <span className="text-3xl font-semibold tracking-tight tabular-nums">
          {formatVdot(current.avg7)} ms
        </span>
        {/* Badge textual: status local do payload (HRV-06/08 — sem
            tradução inventada; null = coletando linha de base). O número
            em destaque é a média 7d — é ela que decide o status (UAT) */}
        <span className="rounded-full border border-border bg-card px-2 py-0.5 text-xs text-muted">
          {current.status ?? "coletando linha de base…"}
        </span>
      </p>
      {/* Contexto (HRV-07/08): a última noite e os limites da banda */}
      <p className="mt-1 text-xs text-muted">
        última noite {formatVdot(current.value)} ms
        {current.band_low != null && current.band_high != null && (
          <>
            {" · banda "}
            {formatVdot(current.band_low)}–{formatVdot(current.band_high)} ms
          </>
        )}
      </p>

      <div className="mt-3 h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
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
            {/* Banda normal por dia (HRV-04/05): stack de base+span; dias
                sem banda (null) quebram a área */}
            <Area
              dataKey="bandBase"
              stackId="band"
              stroke="none"
              fill="transparent"
              dot={false}
              activeDot={false}
              isAnimationActive={false}
            />
            <Area
              dataKey="bandSpan"
              stackId="band"
              stroke="none"
              fill={HRV_COLOR}
              fillOpacity={BAND_OPACITY}
              dot={false}
              activeDot={false}
              isAnimationActive={false}
            />
            {/* Média móvel de 7 dias (HRV-02/03): lacunas preenchidas pela
                janela disponível; janela vazia = sem ponto (connectNulls
                false) */}
            <Line
              type="monotone"
              dataKey="avg7"
              name="média 7d"
              stroke={HRV_COLOR}
              strokeWidth={1.5}
              dot={false}
              connectNulls={false}
            />
            {/* Noites individuais (HRV-01) — fora da banda em âmbar (HRV-13) */}
            <Scatter dataKey="value" shape={NightDot} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <SeriesLegend />
    </div>
  );
}
