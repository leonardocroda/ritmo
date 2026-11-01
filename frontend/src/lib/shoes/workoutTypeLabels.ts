// Workout type labels and VDOT zone colors
// Single source of truth for mapping backend inferred_type to human-readable labels
// If backend changes inferred_type values, update ONLY here

export type WorkoutTypeKey =
  | "facil"
  | "tempo"
  | "limiar"
  | "intervalado"
  | "repeticao"
  | "longao"
  | "progressivo"
  | "prova"
  | "outro";

export type ZoneKey = "easy" | "marathon" | "threshold" | "interval" | "repetition";

export interface WorkoutTypeInfo {
  label: string;
  zoneKey: ZoneKey;
  zoneLabel: string;
}

export const WORKOUT_TYPE_LABELS: Record<WorkoutTypeKey, WorkoutTypeInfo> = {
  facil: { label: "Rodagem fácil", zoneKey: "easy", zoneLabel: "Easy" },
  tempo: { label: "Tempo (maratona)", zoneKey: "marathon", zoneLabel: "Maratona" },
  limiar: { label: "Limiar", zoneKey: "threshold", zoneLabel: "Limiar" },
  intervalado: { label: "Intervalado", zoneKey: "interval", zoneLabel: "Intervalado" },
  repeticao: { label: "Repetições", zoneKey: "repetition", zoneLabel: "Repetição" },
  longao: { label: "Longão", zoneKey: "easy", zoneLabel: "Easy" },
  progressivo: { label: "Progressivo", zoneKey: "marathon", zoneLabel: "Maratona" },
  prova: { label: "Prova", zoneKey: "interval", zoneLabel: "Intervalado" },
  outro: { label: "Outro", zoneKey: "easy", zoneLabel: "Easy" },
};

export const ZONE_COLORS: Record<ZoneKey, string> = {
  easy: "#22c55e",      // green-500
  marathon: "#3b82f6",  // blue-500
  threshold: "#f97316", // orange-500
  interval: "#ef4444",  // red-500
  repetition: "#a855f7", // purple-500
};

export function getWorkoutTypeInfo(tipo: string): WorkoutTypeInfo {
  return WORKOUT_TYPE_LABELS[tipo as WorkoutTypeKey] ?? WORKOUT_TYPE_LABELS.outro;
}

export function getZoneColor(zoneKey: ZoneKey): string {
  return ZONE_COLORS[zoneKey];
}

// Priority order for sorting workout types in overview
export const WORKOUT_TYPE_PRIORITY: WorkoutTypeKey[] = [
  "facil",
  "tempo",
  "limiar",
  "intervalado",
  "repeticao",
  "longao",
  "progressivo",
  "prova",
  "outro",
];

export function compareWorkoutTypes(a: string, b: string): number {
  const idxA = WORKOUT_TYPE_PRIORITY.indexOf(a as WorkoutTypeKey);
  const idxB = WORKOUT_TYPE_PRIORITY.indexOf(b as WorkoutTypeKey);
  if (idxA === -1 && idxB === -1) return 0;
  if (idxA === -1) return 1;
  if (idxB === -1) return -1;
  return idxA - idxB;
}