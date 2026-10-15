// Formatadores PT-BR — port de format_pace/format_duration do renderer
// validado (generate_image.py), mais distância, cadência e temperatura.
// Datas são wall clock do Garmin: exibidas como gravadas, sem conversão
// de fuso (premissa do spec).

import type { InferredType } from "@/lib/api";

/** Pace em M:SS/km (pace_s = segundos por km): 297.7 -> "4:58". */
export function formatPace(paceS: number): string {
  const total = Math.round(paceS);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

/** Duração: H:MM:SS a partir de 1h, M:SS abaixo: 2451 -> "40:51". */
export function formatDuration(durationS: number): string {
  const total = Math.round(durationS);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const mm = String(m).padStart(2, "0");
  const ss = String(s).padStart(2, "0");
  return h > 0 ? `${h}:${mm}:${ss}` : `${m}:${ss}`;
}

/** Distância em km com vírgula e 1 decimal: 8234 -> "8,2 km". */
export function formatKm(meters: number): string {
  return `${(meters / 1000).toFixed(1).replace(".", ",")} km`;
}

/** Cadência em passos por minuto: 155.2 -> "155 spm". */
export function formatCadence(spm: number): string {
  return `${Math.round(spm)} spm`;
}

/** Temperatura com vírgula e 1 decimal: 22.4 -> "22,4 °C". */
export function formatTemp(celsius: number): string {
  return `${celsius.toFixed(1).replace(".", ",")} °C`;
}

/** Data/hora wall clock sem converter fuso: "2026-10-14T07:15:02" -> "14/10/2026 07:15". */
export function formatDateTime(iso: string): string {
  const [date, time = ""] = iso.split("T");
  const [year, month, day] = date.split("-");
  return `${day}/${month}/${year} ${time.slice(0, 5)}`;
}

const TYPE_LABELS: Record<InferredType, string> = {
  prova: "Prova",
  intervalado: "Intervalado",
  limiar: "Limiar",
  tempo: "Tempo",
  progressivo: "Progressivo",
  longao: "Longão",
  facil: "Fácil",
};

/** Rótulo PT-BR do tipo inferido (a API usa ASCII: longao/facil). */
export function formatInferredType(type: InferredType): string {
  return TYPE_LABELS[type];
}
