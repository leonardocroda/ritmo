"use client";

// EvaluateForm — intenção + botão "Avaliar com IA" (EVAL-01/08).
// Select pré-preenchido com o tipo inferido (chaves 1:1 — confirmar é 1
// toque, contrariar é 0) e texto livre opcional de até 500 caracteres.
// Durante a chamada: botão desabilitado com "Analisando treino…" —
// nenhum clique duplo gera segunda chamada (custo de tokens por design).

import { useState } from "react";

import {
  evaluateActivity,
  type ActivityOut,
  type EvaluationOut,
  type InferredType,
} from "@/lib/api";
import { formatInferredType } from "@/lib/format";

// Ordem do plano §4.6: fácil → prova
const INTENT_OPTIONS: InferredType[] = [
  "facil",
  "tempo",
  "limiar",
  "intervalado",
  "longao",
  "progressivo",
  "prova",
];

const MAX_INTENT_TEXT = 500;

export default function EvaluateForm({
  activity,
  pending,
  onEvaluated,
}: {
  activity: ActivityOut;
  /** Existe avaliação em curso (EVAL-08) — botão guarda a fila */
  pending: boolean;
  onEvaluated: (evaluation: EvaluationOut) => void;
}) {
  const [intentType, setIntentType] = useState<InferredType>(
    activity.inferred_type ?? "facil",
  );
  const [intentText, setIntentText] = useState("");
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  async function handleEvaluate() {
    setBusy(true);
    setFailure(null);
    try {
      // Job (EVAL-21): o POST só cria o pending — a resposta é rápida;
      // o guarda real contra fila dupla é a prop `pending`.
      const evaluation = await evaluateActivity(activity.id, {
        intent_type: intentType,
        intent_text: intentText.trim() === "" ? undefined : intentText.trim(),
      });
      onEvaluated(evaluation);
    } catch (err) {
      setFailure(err instanceof Error ? err.message : "Erro inesperado");
    } finally {
      setBusy(false);
    }
  }

  const blocked = busy || pending;

  return (
    <section className="mt-6">
      <h2 className="text-sm font-medium text-muted">Avaliar com IA</h2>
      <div className="mt-2 rounded-xl border border-white/10 bg-card p-3">
        <label className="block text-xs text-muted" htmlFor="intent-type">
          Qual era a intenção do treino?
        </label>
        <select
          id="intent-type"
          value={intentType}
          onChange={(event) => setIntentType(event.target.value as InferredType)}
          disabled={blocked}
          className="mt-1 w-full rounded-lg border border-white/10 bg-background px-3 py-2 text-sm"
        >
          {INTENT_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {formatInferredType(option)}
            </option>
          ))}
        </select>

        <label className="mt-3 block text-xs text-muted" htmlFor="intent-text">
          Contexto (opcional)
        </label>
        <textarea
          id="intent-text"
          value={intentText}
          onChange={(event) => setIntentText(event.target.value)}
          placeholder="era pra ser 30min a 4:15"
          rows={2}
          maxLength={MAX_INTENT_TEXT}
          disabled={blocked}
          className="mt-1 w-full resize-none rounded-lg border border-white/10 bg-background px-3 py-2 text-sm placeholder:text-muted/60"
        />

        <button
          type="button"
          onClick={handleEvaluate}
          disabled={blocked}
          className={
            blocked
              ? "mt-3 w-full rounded-full border border-white/10 bg-card px-4 py-1.5 text-sm font-medium text-muted"
              : "mt-3 w-full rounded-full border border-accent/30 px-4 py-1.5 text-sm font-medium text-accent hover:bg-accent/10"
          }
        >
          {blocked ? "Analisando treino…" : "Avaliar com IA"}
        </button>

        {failure !== null && (
          <p className="mt-2 text-xs text-muted">{failure}</p>
        )}
      </div>
    </section>
  );
}
