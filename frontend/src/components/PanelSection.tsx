// Cabeçalho forte de seção (AD-009 — CLR-12/13/14) — a unidade de
// clareza trans-painel: índice numeral discreto quando a ordem forma um
// passo a passo (Saúde 1–5; Performance narra sem índice), título maior,
// subtítulo sempre visível cobrindo "o que é / por que importa" — nada
// atrás de clique (context.md B) — e selo de fonte/método opcional
// (pill do Vo2maxTrend). Sem card wrapper (context.md D); o espaçamento
// entre seções (mt-8) é claramente maior que o interno (space-y-3).

import type { ReactNode } from "react";

type PanelSectionProps = {
  /** Numeral do passo na ordem do fio condutor (Saúde 1–5). */
  index?: number;
  title: string;
  /** A pergunta que a seção responde + o que ela mostra (1–2 linhas). */
  subtitle: string;
  /** Selo de fonte/método quando o número precisa de origem. */
  badge?: string;
  children: ReactNode;
};

export default function PanelSection({
  index,
  title,
  subtitle,
  badge,
  children,
}: PanelSectionProps) {
  return (
    <section className="mt-8">
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
        {index !== undefined && (
          <span className="text-sm tabular-nums text-muted">{index}.</span>
        )}
        <h2 className="text-base font-semibold tracking-tight">{title}</h2>
        {badge !== undefined && (
          <span className="rounded-full bg-accent/15 px-2 py-0.5 text-sm font-medium text-accent">
            {badge}
          </span>
        )}
      </div>
      <p className="mt-1 text-sm text-muted">{subtitle}</p>
      <div className="mt-3">{children}</div>
    </section>
  );
}
