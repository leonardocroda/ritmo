"use client";

// Mini de volume (mock v0.3 §03, fpanel "Volume · últimas 10 semanas") —
// o contexto da temporada a um glance: Recharts desde a emenda UAT de
// 23/10 (tooltip ao toque, legenda e eixo Y com a escala em km — o
// vocabulário visual da casa), 10 barras neutras com só a semana
// corrente acesa (o gesto de todo gráfico da plataforma) e a sentença
// com os valores do payload (HOME-37). Delta null = "—" (média de 4
// semanas zerada — nunca % inventado) e o segmento ACWR some quando a
// janela da PMC é incompleta (HOME-36: nada inventado).

import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { HomeVolume, HomeWeekPoint } from "@/lib/api";
import { axisLine, chart, legendCaption, tick, tooltipCard } from "@/lib/chartTheme";
import { formatKm } from "@/lib/format";

/** "2026-10-20" -> "20/10" (wall clock, sem conversão de fuso). */
function dayMonth(iso: string): string {
  const [, month, day] = iso.split("-");
  return `${day}/${month}`;
}

/** Delta % com sinal e vírgula PT-BR: 8 -> "+8%", -8.3 -> "−8,3%". */
function formatDeltaPct(deltaPct: number): string {
  const sign = deltaPct > 0 ? "+" : deltaPct < 0 ? "−" : "";
  const rounded = Math.round(deltaPct * 10) / 10;
  const text = Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
  return `${sign}${text.replace(".", ",")}%`;
}

/** ACWR com vírgula PT-BR: 1.1 -> "1,1". */
function formatAcwr(acwr: number): string {
  return acwr.toFixed(1).replace(".", ",");
}

/** Tooltip da semana: início da semana + km (formatKm come metros). */
function WeekTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: HomeWeekPoint }[];
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className={tooltipCard}>
      <p className="font-medium">semana {dayMonth(point.week_start)}</p>
      <p className="mt-1 text-muted">{formatKm(point.km * 1000)}</p>
    </div>
  );
}

export default function VolumeMini({
  volume,
  weeks,
  acwr,
}: {
  volume: HomeVolume;
  weeks: HomeWeekPoint[];
  acwr: number | null;
}) {
  return (
    <div className="rounded-card border border-border bg-card p-4">
      <p className="text-[9.5px] font-bold uppercase tracking-[0.11em] text-muted">
        Volume · últimas 10 semanas
      </p>
      {/* Semana corrente acesa (índice — o service ordena terminando na
          semana corrente), contexto neutro; o eixo Y dá a escala absoluta
          (nada de entender por comparação com a última barra). */}
      <div className="mt-3 h-[92px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={weeks} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
            <XAxis
              dataKey="week_start"
              tickFormatter={dayMonth}
              minTickGap={6}
              axisLine={axisLine}
              tick={tick}
              tickLine={false}
            />
            <YAxis width={30} axisLine={false} tick={tick} tickLine={false} />
            <Tooltip content={<WeekTooltip />} />
            <Bar dataKey="km" name="km" radius={[3, 3, 0, 0]}>
              {weeks.map((week, index) => (
                <Cell
                  key={week.week_start}
                  fill={
                    index === weeks.length - 1 ? chart.subject : chart.context
                  }
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className={legendCaption}>
        <span className="flex items-center gap-1.5">
          <span
            aria-hidden
            className="inline-block h-2.5 w-2.5 rounded-sm"
            style={{ backgroundColor: chart.subject }}
          />
          semana atual
        </span>
        <span className="flex items-center gap-1.5">
          <span
            aria-hidden
            className="inline-block h-2.5 w-2.5 rounded-sm"
            style={{ backgroundColor: chart.context }}
          />
          semanas anteriores
        </span>
      </div>
      <p className="mt-2.5 text-[12.5px] leading-relaxed tabular-nums text-muted">
        <span className="font-semibold text-foreground">
          {formatKm(volume.week_km * 1000)}
        </span>{" "}
        ·{" "}
        {volume.delta_pct !== null ? formatDeltaPct(volume.delta_pct) : "—"} vs
        média de 4 semanas
        {acwr !== null && <> · ACWR {formatAcwr(acwr)}</>}
      </p>
    </div>
  );
}
