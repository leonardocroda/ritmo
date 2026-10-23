"use client";

// Timeline VDOT com faixa honesta (POT-17) — Recharts (AD-008): um ponto
// por entrada (PR/prova/teste), linha tracejada no VDOT corrente e faixa
// sombreada entre corrente e demonstrado (AD-004: a lacuna é o alvo
// honesto, nunca número único). Datas são wall clock: ms construídos em
// UTC e lidos com getters UTC — o dia gravado é o dia exibido, sem
// conversão de fuso (mesma postura do format.ts).

import {
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { TimelinePoint, VdotBlock } from "@/lib/api";
import { axisLine, chart, tick, tooltipCard } from "@/lib/chartTheme";
import { formatDuration, formatKm, formatVdot } from "@/lib/format";

type PlotPoint = TimelinePoint & { x: number };

/** "2026-04-26" -> ms (meia-noite UTC): preserva o dia gravado. */
function isoToMs(date: string): number {
  return Date.parse(`${date}T00:00:00Z`);
}

/** Tick do eixo X: "26/04" — getters UTC sobre meia-noite UTC. */
function tickLabel(ms: number): string {
  const day = String(new Date(ms).getUTCDate()).padStart(2, "0");
  const month = String(new Date(ms).getUTCMonth() + 1).padStart(2, "0");
  return `${day}/${month}`;
}

/** "2026-04-26" -> "26/04/2026" (wall clock, sem conversão de fuso). */
function fullDate(date: string): string {
  const [year, month, day] = date.split("-");
  return `${day}/${month}/${year}`;
}

function TimelineTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: PlotPoint }[];
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className={tooltipCard}>
      <p className="font-medium">{point.label}</p>
      <p className="mt-0.5 text-muted">{fullDate(point.date)}</p>
      <p className="mt-1 text-muted">
        {formatKm(point.distance_m)} em {formatDuration(point.time_s)}
      </p>
      <p className="mt-0.5 font-medium">VDOT {formatVdot(point.vdot)}</p>
    </div>
  );
}

export default function VdotTimeline({ vdot }: { vdot: VdotBlock }) {
  const { current, demonstrated, timeline } = vdot;
  const data: PlotPoint[] = timeline.map((point) => ({
    ...point,
    x: isoToMs(point.date),
  }));

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 12, right: 16, bottom: 4, left: 0 }}>
          <XAxis
            type="number"
            dataKey="x"
            domain={["dataMin - 2592000000", "dataMax + 2592000000"]}
            tickFormatter={tickLabel}
            axisLine={axisLine}
            tick={tick}
            tickLine={false}
          />
          <YAxis
            dataKey="vdot"
            domain={["auto", "auto"]}
            tickFormatter={(value: number) => formatVdot(value)}
            axisLine={false}
            tick={tick}
            tickLine={false}
            width={42}
          />
          <Tooltip content={<TimelineTooltip />} />
          {demonstrated !== null && (
            <ReferenceArea
              y1={current.vdot}
              y2={demonstrated.vdot}
              fill={chart.subject}
              fillOpacity={chart.bandOpacity}
              ifOverflow="extendDomain"
            />
          )}
          <ReferenceLine
            y={current.vdot}
            stroke={chart.context}
            strokeDasharray="4 4"
            ifOverflow="extendDomain"
            label={{
              value: `corrente ${formatVdot(current.vdot)}`,
              position: "insideBottomLeft",
              fill: chart.muted,
              fontSize: 10,
            }}
          />
          <Scatter data={data} fill={chart.subject} />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
