"use client";

// EvaluationCard — card de veredito da avaliação mais recente (EVAL-05)
// + entradas resumidas das anteriores (EVAL-17). Selo por veredito
// (assumption do spec): ✅ on_target/context_explained · ⚠️ too_easy/
// fatigue_signal · ❌ too_hard. Rodapé de método sempre visível —
// modelo, tokens e data (AD-009: auditoria no card). O pct_zona_alvo é
// o número calculado em Python, sanitizado no backend (AD-003).

import type { EvaluationOut, Verdict } from "@/lib/api";
import { formatDateTime } from "@/lib/format";

const VERDICT_SEAL: Record<Verdict, { icon: string; label: string }> = {
  on_target: { icon: "✅", label: "No alvo" },
  context_explained: { icon: "✅", label: "Ajuste adequado ao contexto" },
  too_easy: { icon: "⚠️", label: "Abaixo do alvo" },
  fatigue_signal: { icon: "⚠️", label: "Sinal de fadiga" },
  too_hard: { icon: "❌", label: "Acima do alvo" },
};

/** Lista do veredito — omitida quando vazia (nada inventado). */
function VerdictList({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div className="mt-3">
      <p className="text-xs font-medium uppercase tracking-wide text-muted">{title}</p>
      <ul className="mt-1 space-y-1">
        {items.map((item, index) => (
          <li key={index} className="text-sm">
            • {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function EvaluationCard({
  evaluation,
}: {
  evaluation: EvaluationOut;
}) {
  const verdict = evaluation.verdict_json;
  const seal = VERDICT_SEAL[evaluation.verdict];
  const pct = verdict.execucao_vs_intencao.pct_zona_alvo;
  const tokens = evaluation.tokens_in + evaluation.tokens_out;

  return (
    <section className="mt-6">
      <h2 className="text-sm font-medium text-muted">Avaliação</h2>
      <div className="mt-2 rounded-xl border border-white/10 bg-card p-4">
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm font-medium leading-snug">{verdict.headline}</p>
          <span className="shrink-0 rounded-full bg-accent/15 px-2 py-0.5 text-sm font-medium text-accent">
            {seal.icon} {seal.label}
          </span>
        </div>

        {pct !== null && (
          <p className="mt-2 text-sm text-muted">
            Execução vs intenção: {pct.toFixed(1).replace(".", ",")}% na zona alvo
          </p>
        )}

        <VerdictList
          title="Principais desvios"
          items={verdict.execucao_vs_intencao.principais_desvios}
        />
        <VerdictList title="O que funcionou" items={verdict.o_que_funcionou} />
        <VerdictList title="Corrigir na próxima vez" items={verdict.corrigir_prox_vez} />
        <VerdictList title="Contexto relevante" items={verdict.contexto_relevante} />

        {/* Selo de método (AD-009): confiança, modelo, tokens e data */}
        <p className="mt-3 border-t border-white/10 pt-2 text-xs text-muted">
          Confiança: {verdict.confianca} · {evaluation.model} ·{" "}
          {tokens.toLocaleString("pt-BR")} tokens ·{" "}
          {formatDateTime(evaluation.created_at)}
        </p>
      </div>
    </section>
  );
}

/** Entradas resumidas das avaliações anteriores (EVAL-17): data, selo, headline. */
export function EvaluationHistory({
  evaluations,
}: {
  evaluations: EvaluationOut[];
}) {
  if (evaluations.length === 0) return null;
  return (
    <section className="mt-4">
      <h3 className="text-sm font-medium text-muted">Avaliações anteriores</h3>
      <ul className="mt-2 space-y-2">
        {evaluations.map((item) => {
          const seal = VERDICT_SEAL[item.verdict];
          return (
            <li
              key={item.id}
              className="flex items-center justify-between gap-2 rounded-xl border border-white/10 bg-card px-3 py-2 text-sm"
            >
              <span className="leading-snug">{item.verdict_json.headline}</span>
              <span className="shrink-0 text-xs text-muted">
                {seal.icon} {formatDateTime(item.created_at)}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
