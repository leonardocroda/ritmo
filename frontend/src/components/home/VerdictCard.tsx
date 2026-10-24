"use client";

"use client";

// Card-veredito (mock v0.3 §03) — o herói da Home: eyebrow "Hoje · [dia,
// data]", frase display 38px sentence case, os 3 chips de sinal (dot
// semântico + valor + estado — dado antigo mostra a data, HOME-16) e a
// strip de carga dos últimos 7 dias — Recharts desde a emenda UAT de
// 23/10 (tooltip ao toque + legenda, o vocabulário visual da casa),
// neutra com só hoje aceso (o gesto de todo gráfico da plataforma).
// Dia sem carga = barra ausente, o dia segue no eixo: descanso é
// informação, não lacuna (HOME-15). Zero cor literal — o neutro/lime
// vem do chartTheme (como nos charts), os tons semânticos das classes
// do tema (globals.css).

import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
} from "recharts";

import type { ReactNode } from "react";

import type { HomeSignals, HomeStripPoint, HomeVerdict } from "@/lib/api";
import { axisLine, chart, legendCaption, tick, tooltipCard } from "@/lib/chartTheme";

// O mesmo piso de sono do painel Saúde (backend SLEEP_FLOOR_S = 7h): o
// chip acende alerta abaixo dele — o agravante da V1, nunca uma régua nova.
const SLEEP_FLOOR_S = 25200;

/** Data-only ISO ("2026-10-23") em partes — `new Date(iso)` interpretaria
 * UTC e atrasaria um dia em fuso negativo; a data exibida é a que o
 * backend gravou (wall clock, premissa do lib/format). */
function dateParts(iso: string): [number, number, number] {
  const [year, month, day] = iso.split("-");
  return [Number(year), Number(month), Number(day)];
}

/** "21/10" — a data do dado quando ele não é de hoje (HOME-16). */
function dayMonth(iso: string): string {
  const [, month, day] = dateParts(iso);
  return `${day}/${month}`;
}

/** "21/10/2026" — o dia completo no tooltip (padrão PmcChart). */
function fullDay(iso: string): string {
  const [year, month, day] = dateParts(iso);
  return `${day}/${month}/${year}`;
}

/** Eyebrow do dia: "sexta, 23 de outubro" (Intl pt-BR — o formatWeekday
 * devolve o rótulo curto; o card pede o longo, decisão do mock §03). */
function eyebrowDate(iso: string): string {
  const [year, month, day] = dateParts(iso);
  return new Intl.DateTimeFormat("pt-BR", {
    weekday: "long",
    day: "numeric",
    month: "long",
  }).format(new Date(year, month - 1, day));
}

/** Duração de sono no ritmo do mock: 27720s -> "7h42". */
function sleepDuration(durationS: number): string {
  const hours = Math.floor(durationS / 3600);
  const minutes = Math.round((durationS % 3600) / 60);
  return `${hours}h${String(minutes).padStart(2, "0")}`;
}

/** Delta de sono em minutos com sinal: 1920 -> "+32min", -690 -> "−11min". */
function sleepDelta(deltaS: number): string {
  const minutes = Math.round(deltaS / 60);
  return `${minutes >= 0 ? "+" : "−"}${Math.abs(minutes)}min`;
}

/** TSB com sinal e vírgula PT-BR: 5.2 -> "+5,2" (mock "Forma +5,2"). */
function formatTsb(tsb: number): string {
  const sign = tsb > 0 ? "+" : "";
  return `${sign}${tsb.toFixed(1).replace(".", ",")}`;
}

/** Chip de sinal: dot semântico + conteúdo — nada de número órfão. */
function SignalChip({ dot, children }: { dot: string; children: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background px-2.5 py-1 text-[11.5px] text-muted">
      <span className={`size-1.5 shrink-0 rounded-full ${dot}`} />
      {children}
    </span>
  );
}

/** Tooltip da strip: dia completo + carga diária arredondada (mesma
 * fonte da PMC — aggregate_daily_loads). */
function StripTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: HomeStripPoint }[];
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className={tooltipCard}>
      <p className="font-medium">{fullDay(point.date)}</p>
      <p className="mt-1 text-muted">carga {Math.round(point.load)}</p>
    </div>
  );
}

export default function VerdictCard({
  verdict,
  signals,
  strip,
  date,
}: {
  verdict: HomeVerdict;
  signals: HomeSignals;
  strip: HomeStripPoint[];
  date: string;
}) {
  const { hrv, sleep, fitness } = signals;

  return (
    <section className="rounded-card border border-border bg-raised px-4 pb-3.5 pt-4">
      <p className="text-[11px] font-bold uppercase tracking-[0.13em] text-muted">
        Hoje · {eyebrowDate(date)}
      </p>
      <h2 className="mt-2.5 text-[38px] font-semibold leading-[1.05] tracking-[-0.025em]">
        {verdict.phrase}
      </h2>

      {/* O porquê em chips: valor + estado, data quando o dado não é de
          hoje (comparação de datas ISO — lexicográfica é correta). */}
      <div className="mt-3 flex flex-wrap gap-1.5 tabular-nums">
        {hrv === null ? (
          <SignalChip dot="bg-muted">HRV · coletando linha de base</SignalChip>
        ) : (
          <SignalChip
            dot={
              hrv.status === "BALANCED"
                ? "bg-good"
                : hrv.status === "UNBALANCED"
                  ? "bg-attention"
                  : "bg-muted"
            }
          >
            {`HRV ${Math.round(hrv.value)}ms · ${
              hrv.status === "BALANCED"
                ? "na faixa"
                : hrv.status === "UNBALANCED"
                  ? "fora da faixa"
                  : "coletando linha de base"
            }${hrv.as_of < date ? ` · ${dayMonth(hrv.as_of)}` : ""}`}
          </SignalChip>
        )}
        {sleep === null ? (
          <SignalChip dot="bg-muted">Sono · sem dado</SignalChip>
        ) : (
          <SignalChip
            dot={sleep.duration_s < SLEEP_FLOOR_S ? "bg-alert" : "bg-good"}
          >
            {`Sono ${sleepDuration(sleep.duration_s)}${
              sleep.delta_s !== null ? ` · ${sleepDelta(sleep.delta_s)}` : ""
            }${sleep.as_of < date ? ` · ${dayMonth(sleep.as_of)}` : ""}`}
          </SignalChip>
        )}
        {fitness === null || fitness.tsb === null ? (
          <SignalChip dot="bg-muted">Forma · sem dado</SignalChip>
        ) : (
          <SignalChip dot={fitness.tsb > 0 ? "bg-good" : "bg-muted"}>
            {`Forma ${formatTsb(fitness.tsb)}${
              fitness.as_of < date ? ` · ${dayMonth(fitness.as_of)}` : ""
            }`}
          </SignalChip>
        )}
      </div>

      {/* Strip de 7 dias em Recharts: neutra, só hoje aceso (data
          comparada, não índice — padrão PmcChart); carga 0 = barra
          ausente, o dia segue no eixo. Toque/hover mostra o valor. */}
      <div className="mt-3.5 h-[84px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={strip} margin={{ top: 4, right: 4, bottom: 0, left: 4 }}>
            <XAxis
              dataKey="date"
              tickFormatter={dayMonth}
              axisLine={axisLine}
              tick={tick}
              tickLine={false}
            />
            <Tooltip content={<StripTooltip />} />
            <Bar dataKey="load" name="carga" radius={[3, 3, 0, 0]}>
              {strip.map((point) => (
                <Cell
                  key={point.date}
                  fill={point.date === date ? chart.subject : chart.context}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className={legendCaption}>
        <span>carga</span>
        <span className="flex items-center gap-1.5">
          <span
            aria-hidden
            className="inline-block h-2.5 w-2.5 rounded-sm"
            style={{ backgroundColor: chart.subject }}
          />
          hoje
        </span>
        <span className="flex items-center gap-1.5">
          <span
            aria-hidden
            className="inline-block h-2.5 w-2.5 rounded-sm"
            style={{ backgroundColor: chart.context }}
          />
          dias anteriores
        </span>
      </div>
    </section>
  );
}
