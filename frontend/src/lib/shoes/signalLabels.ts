// Degradation signal labels and tooltips
// Maps backend signal keys to human-readable labels with explanations

export type SignalKey =
  | "gct_ms"
  | "vert_osc_cm"
  | "avg_cadence"
  | "ef"
  | "hr_drift"
  | "rpe";

export interface SignalInfo {
  label: string;
  tooltip: string;
  higherIsWorse: boolean;
  unit: string;
}

export const SIGNAL_LABELS: Record<SignalKey, SignalInfo> = {
  gct_ms: {
    label: "Tempo de contato no solo (GCT)",
    tooltip: "Tempo que o pé fica no chão a cada passada. Aumento = menos eficiência, possível fadiga do tênis.",
    higherIsWorse: true,
    unit: "ms",
  },
  vert_osc_cm: {
    label: "Oscilação vertical",
    tooltip: "Quanto o corpo sobe/desce a cada passada. Aumento = mais desperdício de energia vertical.",
    higherIsWorse: true,
    unit: "cm",
  },
  avg_cadence: {
    label: "Cadência",
    tooltip: "Passadas por minuto. Queda = passadas mais longas/forçadas, possível perda de responsividade.",
    higherIsWorse: false, // lower is worse
    unit: "spm",
  },
  ef: {
    label: "Fator de eficiência (EF)",
    tooltip: "Relação velocidade/FC. Queda = coração trabalha mais pela mesma velocidade.",
    higherIsWorse: false, // lower is worse
    unit: "",
  },
  hr_drift: {
    label: "Deriva de FC",
    tooltip: "Aumento da FC durante a corrida em pace constante. Aumento = menos eficiência cardiovascular.",
    higherIsWorse: true,
    unit: "bpm",
  },
  rpe: {
    label: "Percepção de esforço (RPE)",
    tooltip: "Esforço percebido (1-10). Aumento = sente mais difícil no mesmo pace.",
    higherIsWorse: true,
    unit: "pontos",
  },
};

export function getSignalInfo(sinal: string): SignalInfo {
  return SIGNAL_LABELS[sinal as SignalKey] ?? {
    label: sinal,
    tooltip: "",
    higherIsWorse: true,
    unit: "",
  };
}

export function getDirection(delta: number, higherIsWorse: boolean): "piorou" | "melhorou" | "estável" {
  const threshold = 0.01;
  if (Math.abs(delta) <= threshold) return "estável";
  if (higherIsWorse) {
    return delta > 0 ? "piorou" : "melhorou";
  }
  return delta > 0 ? "melhorou" : "piorou";
}

export function getDirectionColor(direction: "piorou" | "melhorou" | "estável"): string {
  switch (direction) {
    case "piorou": return "text-coral";
    case "melhorou": return "text-lime";
    default: return "text-muted";
  }
}

export function getDirectionBg(direction: "piorou" | "melhorou" | "estável"): string {
  switch (direction) {
    case "piorou": return "bg-coral/15 text-coral border-coral/30";
    case "melhorou": return "bg-lime/15 text-lime border-lime/30";
    default: return "bg-border text-muted border-border";
  }
}