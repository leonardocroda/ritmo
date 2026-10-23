"use client";

// Mini de volume (mock v0.3 §03, fpanel "Volume · últimas 10 semanas") —
// o contexto da temporada a um glance: 10 barras neutras com só a
// semana corrente acesa (o gesto de todo gráfico da plataforma) e a
// sentença com os valores do payload (HOME-37). Delta null = "—"
// (média de 4 semanas zerada — nunca % inventado) e o segmento ACWR
// some quando a janela da PMC é incompleta (HOME-36: nada inventado).

import type { HomeVolume, HomeWeekPoint } from "@/lib/api";
import { chart } from "@/lib/chartTheme";
import { formatKm } from "@/lib/format";

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

export default function VolumeMini({
  volume,
  weeks,
  acwr,
}: {
  volume: HomeVolume;
  weeks: HomeWeekPoint[];
  acwr: number | null;
}) {
  // Escala das barras: altura proporcional à maior semana da série
  // (janela toda zerada -> todas com altura 0, descanso é informação).
  const maxKm = Math.max(...weeks.map((week) => week.km));

  return (
    <div className="rounded-card border border-border bg-card p-4">
      <p className="text-[9.5px] font-bold uppercase tracking-[0.11em] text-muted">
        Volume · últimas 10 semanas
      </p>
      <div
        className="mt-3 flex h-16 items-end gap-1.5"
        role="img"
        aria-label="Volume das últimas 10 semanas"
      >
        {weeks.map((week, index) => {
          const isCurrent = index === weeks.length - 1;
          return (
            <span
              key={week.week_start}
              className="flex-1 rounded-t-[4px]"
              style={{
                height: `${maxKm > 0 ? (week.km / maxKm) * 100 : 0}%`,
                backgroundColor: isCurrent ? chart.subject : chart.context,
              }}
            />
          );
        })}
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
