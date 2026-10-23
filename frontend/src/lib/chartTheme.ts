// Tema de gráfico compartilhado — "contexto em neutro, um único destaque
// lime" (DSN-11..15). Famílias semânticas: lime = recuperação/desempenho/
// "hoje" · alert (coral) = carga/fadiga/estresse · attention (âmbar) = fora
// de banda/REM · muted/context = o resto.
//
// Coexistência das zonas VDOT (DSN-16, AD-022): as cores das zonas vêm do
// backend (`ZoneMeta.color` — fonte única) e só aparecem em superfície de
// treino; o lime da marca é deliberadamente distinto do verde-easy de zona
// — nenhuma cor deste tema reutiliza matiz de zona fora de contexto de
// treino.

export const chart = {
  axis: "#354039", // linha de base + eixos (hairline)
  muted: "#A1AAA9", // ticks e labels
  context: "#4A574E", // séries/barras de contexto
  subject: "#B7F36B", // lime — destaque "hoje" e sujeitos de recuperação/desempenho
  attention: "#E9B44C", // fora da banda, REM, padrões de custo
  alert: "#EF6757", // fadiga/estresse
  bandOpacity: 0.06, // banda pessoal (fill do sujeito)
} as const;

export const tick = { fill: chart.muted, fontSize: 10 } as const; // prop de tick Recharts
export const axisLine = { stroke: chart.axis } as const; // axisLine do XAxis

/** Cartão do tooltip: surface raio 12 com borda (DSN-11). O utilitário
 * `border` (largura) acompanha o `border-border` (cor) — o preflight do
 * Tailwind zera a largura, e a borda é requisito do spec. */
export const tooltipCard = "rounded-ctl border border-border bg-card px-3 py-2 text-xs";

export const legendCaption =
  "mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted";
