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

/** VDOT com 1 casa e vírgula PT-BR: 50.2 -> "50,2". */
export function formatVdot(vdot: number): string {
  return vdot.toFixed(1).replace(".", ",");
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
  repeticao: "Repetição",
  outro: "Outro",
};

/** Rótulo PT-BR do tipo inferido (a API usa ASCII: longao/facil). */
export function formatInferredType(type: InferredType): string {
  return TYPE_LABELS[type];
}

/** Duração de sono em horas, vírgula e 1 casa: 22860 -> "6,3 h". */
export function formatHours(seconds: number): string {
  return `${(seconds / 3600).toFixed(1).replace(".", ",")} h`;
}

/** Minuto do dia -> HH:MM (wall clock local, já convertido no backend):
 * 1336 -> "22:16". Médias fracionárias (regularity) arredondam. */
export function formatClock(minuteOfDay: number): string {
  const total = Math.round(minuteOfDay);
  const h = Math.floor(total / 60);
  const m = total % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

const WEEKDAY_LABELS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"];

/** Rótulo PT-BR do weekday 0..6 (seg..dom) — a API usa número, o acento
 * é camada de exibição (padrão ASCII na API/acento na UI). */
export function formatWeekday(weekday: number): string {
  return WEEKDAY_LABELS[weekday];
}
