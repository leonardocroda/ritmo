"use client";

// Regularidade + média de duração por dia da semana (HLT-16): cards com
// deitar/acordar médios (minutos locais — o fuso já foi convertido no
// backend, exibidos via formatClock) e Recharts BarChart com as 7 entradas
// do weekday_pattern (rótulos formatWeekday, domínio começando em 0).
// regularity null -> cards "—" (noite sem horário não inventa régua).

import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { SleepBlock, WeekdayEntry } from "@/lib/api";
import { axisLine, chart, tick, tooltipCard } from "@/lib/chartTheme";
import { formatClock, formatHours, formatWeekday, formatVdot } from "@/lib/format";

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-card border border-border bg-card px-2.5 py-2">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="mt-0.5 text-sm font-medium tabular-nums">{value}</dd>
    </div>
  );
}

/** Entrada em horas para as barras (o payload traz segundos; dia vazio -> null). */
type WeekdayBar = WeekdayEntry & { hours: number | null };

/** Tick do eixo Y em horas — vírgula PT-BR só quando fracionário. */
function hourTick(hours: number): string {
  return Number.isInteger(hours) ? String(hours) : formatVdot(hours);
}

function WeekdayTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: WeekdayBar }[];
}) {
  if (!active || !payload?.length) return null;
  const entry = payload[0].payload;
  return (
    <div className={tooltipCard}>
      <p className="font-medium">{formatWeekday(entry.weekday)}</p>
      <p className="mt-1 text-muted">
        Média{" "}
        {entry.avg_duration_s !== null ? formatHours(entry.avg_duration_s) : "—"} ·{" "}
        {entry.nights} noites
      </p>
    </div>
  );
}

export default function WeekdayPattern({ sleep }: { sleep: SleepBlock }) {
  const { regularity, weekday_pattern } = sleep;
  const bars: WeekdayBar[] = weekday_pattern.map((entry) => ({
    ...entry,
    hours: entry.avg_duration_s !== null ? entry.avg_duration_s / 3600 : null,
  }));
  // "Hoje" no mesmo formato da API: weekday 0..6 = seg..dom (formatWeekday),
  // não o getDay() do JS (0 = domingo)
  const todayWeekday = (new Date().getDay() + 6) % 7;

  return (
    <div>
      <dl className="grid grid-cols-2 gap-2">
        {/* regularity null = nenhuma noite com horário na janela — "—" */}
        <StatCard
          label="Deitar médio"
          value={regularity !== null ? formatClock(regularity.avg_bed_min) : "—"}
        />
        <StatCard
          label="Acordar médio"
          value={regularity !== null ? formatClock(regularity.avg_wake_min) : "—"}
        />
      </dl>

      <div className="mt-3 h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={bars} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
            <XAxis
              dataKey="weekday"
              tickFormatter={(weekday: number) => formatWeekday(weekday)}
              axisLine={axisLine}
              tick={tick}
              tickLine={false}
            />
            {/* Domínio começando em 0 (média de duração não tem base flutuante) */}
            <YAxis
              width={38}
              domain={[0, "auto"]}
              axisLine={false}
              tick={tick}
              tickLine={false}
              tickFormatter={hourTick}
            />
            <Tooltip content={<WeekdayTooltip />} />
            {/* Dia vazio (avg null) não desenha barra — nada inventado.
                DSN-13: barras de contexto, o dia de hoje em lime */}
            <Bar dataKey="hours" name="média" fill={chart.context} fillOpacity={0.8}>
              {bars.map((bar) => (
                <Cell
                  key={bar.weekday}
                  fill={bar.weekday === todayWeekday ? chart.subject : chart.context}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
