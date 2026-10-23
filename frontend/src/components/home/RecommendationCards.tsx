"use client";

// Cards de recomendação (mock v0.3 §03, abaixo da dobra) — o par
// frase+ação é o produto: cada card `Recomendação · regra` carrega o
// texto, a linha de apoio (só a R5 tem copy de apoio) e a tag why com
// os sinais que sustentam a recomendação (HOME-31). O dot no cabeçalho
// leva o tom semântico — a Home fala baixo no dia comum (neutral = muted).

import type { HomeRecommendation } from "@/lib/api";

const DOT_BY_TONE: Record<string, string> = {
  good: "bg-good",
  attention: "bg-attention",
  alert: "bg-alert",
  neutral: "bg-muted",
};

export default function RecommendationCards({
  recommendations,
}: {
  recommendations: HomeRecommendation[];
}) {
  return (
    <div className="space-y-3">
      {recommendations.map((rec) => (
        <article
          key={rec.text}
          className="rounded-card border border-border bg-card p-4"
        >
          <div className="flex items-center gap-1.5">
            <span
              className={`size-[7px] shrink-0 rounded-full ${DOT_BY_TONE[rec.tone] ?? DOT_BY_TONE.neutral}`}
            />
            <span className="text-[11px] font-bold uppercase tracking-[0.13em] text-muted">
              Recomendação · regra
            </span>
          </div>
          <h3 className="mt-2 text-base font-semibold">{rec.text}</h3>
          {rec.support !== null && (
            <p className="mt-1 text-[12.5px] leading-relaxed text-muted">
              {rec.support}
            </p>
          )}
          {rec.why !== null && (
            <span className="mt-2.5 inline-flex rounded-full border border-border px-2.5 py-1 text-[11px]">
              por quê: {rec.why}
            </span>
          )}
        </article>
      ))}
    </div>
  );
}
