"use client";

// Equilíbrio de vida (HLT-23/24) — checklist de força (2×/semana: streak
// ISO em semanas, semanas atingidas na janela e a semana corrente em
// andamento reportada à parte) e yoga (sessões na janela + média/semana).
// Zeros e ausências aparecem como estão — streak 0 é recado, não erro
// (nenhum número inventado).

import type { Lifestyle as LifestyleData } from "@/lib/api";

/** Contagem com plural PT-BR: 1 sessão / 2 sessões. */
function count(n: number, one: string, many: string): string {
  return `${n} ${n === 1 ? one : many}`;
}

/** Média com 1 casa e vírgula PT-BR (padrão format.ts): 1.4 -> "1,4". */
function formatAvg(value: number): string {
  return value.toFixed(1).replace(".", ",");
}

export default function Lifestyle({ lifestyle }: { lifestyle: LifestyleData }) {
  const { strength, yoga } = lifestyle;
  return (
    <div className="grid grid-cols-2 gap-2">
      {/* Streak 0 aparece como está — é recado, não erro (HLT-23) */}
      <div className="rounded-xl border border-border bg-card px-3 py-2">
        <p className="text-xs text-muted">Força 2×/semana</p>
        <p className="mt-0.5 text-sm font-medium tabular-nums">
          {count(strength.streak_weeks, "semana", "semanas")} de streak
        </p>
        <p className="mt-1.5 text-xs text-muted">
          {strength.weeks_hit}/{strength.weeks_total} semanas na janela
        </p>
        <p className="text-xs text-muted">
          Semana corrente (em andamento):{" "}
          {count(strength.current_week_sessions, "sessão", "sessões")}
        </p>
      </div>
      <div className="rounded-xl border border-border bg-card px-3 py-2">
        <p className="text-xs text-muted">Yoga</p>
        <p className="mt-0.5 text-sm font-medium tabular-nums">
          {count(yoga.sessions, "sessão", "sessões")}
        </p>
        <p className="mt-1.5 text-xs text-muted">{formatAvg(yoga.per_week_avg)}/semana</p>
      </div>
    </div>
  );
}
