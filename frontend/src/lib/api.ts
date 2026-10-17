// Cliente tipado da API — espelha os contratos do backend (designs do
// garmin-sync e workouts-list). A UI lê exclusivamente daqui, nunca do
// Garmin (AD-002): o sync polleia `JobOut` e os painéis leem o domínio
// de leitura `activities`.

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Contadores de progresso — schema exato do stats_json (SYNC-05/06). */
export type SyncStats = {
  step: string;
  message: string;
  activities_new: number;
  activities_updated: number;
  splits: number;
  sleep_days: number;
  hrv_days: number;
  rhr_days: number;
  battery_days: number;
  stress_days: number;
  records: number;
  calls_made: number;
  duration_s: number;
  warnings: { tipo: string; erro: string }[];
  reauth_needed: boolean;
};

export type JobStatus = "pending" | "running" | "done" | "error";

/** Espelho do `JobOut` do router (backend/app/garmin/router.py). */
export type JobOut = {
  id: number;
  status: JobStatus;
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
  stats: SyncStats | null;
};

/** Resposta do `POST /api/sync` (201) — SYNC-01. */
export type JobCreated = { id: number; status: JobStatus };

/** Resposta do `GET /api/sync/jobs/latest` — job null quando nunca houve sync. */
export type LatestJob = { job: JobOut | null };

async function parseError(res: Response): Promise<ApiError> {
  let detail = `Erro HTTP ${res.status}`;
  try {
    const body: unknown = await res.json();
    const raw = (body as { detail?: unknown })?.detail;
    if (typeof raw === "string") {
      detail = raw;
    } else if (raw != null) {
      detail = JSON.stringify(raw);
    }
  } catch {
    // resposta sem corpo JSON — o status já é a mensagem
  }
  return new ApiError(res.status, detail);
}

/** Erro de API com o status HTTP — a UI distingue 404 (inexistente) de falha geral. */
export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

/** Cria um job de sync (SYNC-01). 409 = já existe job ativo (SYNC-02). */
export async function startSync(): Promise<JobCreated> {
  const res = await fetch(`${API_BASE}/api/sync`, { method: "POST" });
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as JobCreated;
}

/** Último job do usuário — o que a UI poleia a cada 2s (SYNC-05). */
export async function getLatestJob(): Promise<LatestJob> {
  const res = await fetch(`${API_BASE}/api/sync/jobs/latest`, {
    cache: "no-store",
  });
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as LatestJob;
}

// ---- Painel Treinos: contratos do design workouts-list ----

/** Tipos inferidos em ASCII na API; acento fica na camada de exibição (design). */
export type InferredType =
  | "prova"
  | "intervalado"
  | "limiar"
  | "tempo"
  | "progressivo"
  | "longao"
  | "facil";

/** Filtro da lista: corridas (default) ou todas as atividades. */
export type ActivityTypeFilter = "running" | "all";

/** Espelho do `ActivityListItem` (backend/app/activities/router.py). */
export type ActivityListItem = {
  id: number;
  start_time: string;
  activity_type: string;
  name: string | null;
  distance_m: number;
  duration_s: number;
  pace_s: number | null;
  avg_hr: number | null;
  inferred_type: InferredType | null;
  evaluated: boolean;
};

/** Espelho do `ActivityListOut` — {items, total, limit, offset} (spec). */
export type ActivityListOut = {
  items: ActivityListItem[];
  total: number;
  limit: number;
  offset: number;
};

/** Espelho do `ActivityOut` do detalhe. */
export type ActivityOut = {
  id: number;
  start_time: string;
  name: string | null;
  distance_m: number;
  duration_s: number;
  pace_s: number | null;
  avg_hr: number | null;
  max_hr: number | null;
  avg_cadence: number | null;
  elevation_gain_m: number | null;
  aerobic_te: number | null;
  anaerobic_te: number | null;
  training_load: number | null;
  evaluated: boolean;
  inferred_type: InferredType | null;
  structure: string | null;
};

/** Espelho do `SplitOut` — volta já classificada por zona no backend. */
export type SplitOut = {
  idx: number;
  dist_m: number | null;
  duration_s: number | null;
  pace_s: number | null;
  avg_hr: number | null;
  avg_cadence: number | null;
  avg_temperature: number | null;
  elevation_m: number | null;
  intensity_type: string | null;
  zone: string | null;
  km_label: string;
};

export type ZoneKey =
  | "easy"
  | "marathon"
  | "threshold"
  | "interval"
  | "repetition";

/** Espelho do `ZoneMetaOut` — cor definida no backend (fonte única). */
export type ZoneMeta = {
  key: ZoneKey;
  label: string;
  pace_range: string;
  color: string;
};

/** Bloco consistency (TRN-21..25). `null` no backend quando <8km ou <4 voltas;
 * `cadence_fade_spm` só existe com cadência suficiente (nenhum número inventado). */
export type Consistency = {
  first_half_pace_s: number | null;
  second_half_pace_s: number | null;
  balance_delta_s: number | null;
  balance_delta_pct: number | null;
  first_half_hr: number | null;
  second_half_hr: number | null;
  hr_drift_bpm: number | null;
  decoupling_pct: number | null;
  cadence_fade_spm?: number;
};

/** Faixa de contexto — cada campo null quando ausente; a UI exibe só o que existir. */
export type ContextOut = {
  sleep: { duration_s: number; score: number | null } | null;
  hrv: { value: number; status: string | null } | null;
  rhr: { value: number } | null;
  temperature_c?: number;
};

/** Espelho do `ActivityDetailOut` do detalhe (TRN-13/19/26/27). */
export type ActivityDetailOut = {
  activity: ActivityOut;
  splits: SplitOut[];
  zones: ZoneMeta[];
  hr_color: string;
  consistency: Consistency | null;
  context: ContextOut;
};

/** Lista paginada de atividades (TRN-04/05/06). 422 para limit/offset inválidos. */
export async function getActivities(
  options: { activityType?: ActivityTypeFilter; limit?: number; offset?: number } = {},
): Promise<ActivityListOut> {
  const params = new URLSearchParams();
  if (options.activityType) params.set("activity_type", options.activityType);
  if (options.limit !== undefined) params.set("limit", String(options.limit));
  if (options.offset !== undefined) params.set("offset", String(options.offset));
  const query = params.toString();
  const res = await fetch(`${API_BASE}/api/activities${query ? `?${query}` : ""}`, {
    cache: "no-store",
  });
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as ActivityListOut;
}

/** Detalhe do treino (TRN-13). 404 = id inexistente (ApiError.status). */
export async function getActivityDetail(id: number): Promise<ActivityDetailOut> {
  const res = await fetch(`${API_BASE}/api/activities/${id}`, {
    cache: "no-store",
  });
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as ActivityDetailOut;
}

// ---- Painel Potencial: contratos do design potential-panel + panel-clarity ----

/** Distâncias canônicas (ASCII na API; acento na exibição — design). */
export type CanonicalEvent = "5K" | "10K" | "HALF_MARATHON" | "MARATHON";

/** Ponto da timeline VDOT — PR, prova ou teste de calibração (POT-08). */
export type TimelinePoint = {
  date: string;
  vdot: number;
  source: string;
  label: string;
  distance_m: number;
  time_s: number;
};

/** Bloco vdot — corrente (arquivo), demonstrado (maior ponto) e faixa honesta. */
export type VdotBlock = {
  current: { vdot: number; source: string; test_date: string };
  demonstrated: { vdot: number; source: string; date: string } | null;
  gap_pct: number | null;
  timeline: TimelinePoint[];
};

/** Linha de previsão por distância — null = estimativa ausente ("—"). */
export type PredictionRow = {
  garmin_s: number | null;
  riegel_s: number | null;
  vdot_s: number | null;
  average_s: number | null;
  pr_s: number | null;
  pr_date: string | null;
};

export type Vo2maxBlock = {
  points: { date: string; value: number }[];
};

export type DecayRow = {
  event: CanonicalEvent;
  real_pace_s: number;
  ideal_pace_s: number;
  delta_pct: number;
};

/** Espelho do `PotentialOut` (backend/app/potential/router.py) — sem
 * `pmc` e sem janela `days` (CLR-03): a curva de carga é contrato
 * exclusivo do Painel Saúde (`PmcBlock` abaixo). */
export type PotentialOut = {
  vdot: VdotBlock;
  predictions: Record<CanonicalEvent, PredictionRow>;
  vo2max: Vo2maxBlock | null;
  decay: DecayRow[];
};

/** Painel Potencial inteiro em 1 payload (POT-11) — sem query params:
 * o `days` morreu junto com o `pmc` e o cliente limpo não envia nada
 * (CLR-04: um `?days=` qualquer seria ignorado pelo backend). */
export async function getPotential(): Promise<PotentialOut> {
  const res = await fetch(`${API_BASE}/api/potential`, {
    cache: "no-store",
  });
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as PotentialOut;
}

// ---- Painel Saúde: contratos do design health-panel + panel-clarity ----

/** Ponto de sono — horários já locais no backend ("HH:MM"), a UI nunca
 * converte fuso (design §Contrato). */
export type SleepPoint = {
  date: string;
  duration_s: number;
  score: number | null;
  rem_pct: number | null;
  deep_pct: number | null;
  light_pct: number | null;
  awakenings: number | null;
  bed_local: string | null;
  wake_local: string | null;
};

export type BelowFloor = { nights: number; pct: number };

/** Weekday 0..6 = seg..dom (o rótulo PT-BR é camada de exibição — formatWeekday). */
export type WeekdayEntry = {
  weekday: number;
  avg_duration_s: number | null;
  nights: number;
};

/** Médias em minutos do dia local (o truque ±12h é do backend). */
export type Regularity = { avg_bed_min: number; avg_wake_min: number };

/** Bloco sono — piso/banda são réguas do payload (a UI não inventa régua). */
export type SleepBlock = {
  days: number;
  floor_s: number;
  rem_band: number[];
  below_floor: BelowFloor;
  regularity: Regularity | null;
  weekday_pattern: WeekdayEntry[];
  points: SleepPoint[];
};

/** Dia corrido da janela de exibição (hrv-baseline): noite individual
 * (null = sem captura), média móvel 7d e banda do dia (null sob o
 * threshold de 14 valores na janela de 60 dias). */
export type HrvPoint = {
  date: string;
  value: number | null;
  avg7: number | null;
  band_low: number | null;
  band_high: number | null;
};

/** Último dia com dado — status local BALANCED/UNBALANCED (média 7d vs
 * banda, limites inclusos) ou null ("coletando linha de base"); o status
 * cru da Garmin saiu do contrato do Saúde. */
export type HrvCurrent = {
  date: string;
  value: number;
  avg7: number;
  band_low: number | null;
  band_high: number | null;
  status: string | null;
};

/** HRV científico — `points` são dias corridos; `current` é o último com dado. */
export type HrvBlock = { points: HrvPoint[]; current: HrvCurrent };

export type RhrPoint = { date: string; value: number };
export type RhrBlock = { points: RhrPoint[]; baseline: number };

export type StressPoint = { date: string; avg: number };
export type StressBlock = { points: StressPoint[]; avg_window: number };

/** Ponto da PMC (contrato exclusivo do Painel Saúde) — null espelha a
 * linha do banco (janela 28d incompleta). */
export type PmcPoint = {
  date: string;
  ctl: number | null;
  atl: number | null;
  tsb: number | null;
  acwr: number | null;
};

/** Bloco Carga de treino (CLR-01) — contrato EXCLUSIVO do Painel Saúde
 * (o Potencial perdeu o bloco — CLR-03): janela `days` única da Saúde;
 * sem linhas em `load` -> null (CLR-02 — estado vazio, não erro). */
export type PmcBlock = {
  days: number;
  points: PmcPoint[];
  current: PmcPoint;
};

/** Bucket do dose-resposta — média null = bucket vazio ("—" na UI). */
export type DoseBucket = {
  nights: number;
  avg_hrv: number | null;
  avg_score: number | null;
};

export type DoseResponse = {
  short: DoseBucket;
  adequate: DoseBucket;
  neutral_nights: number;
};

export type Strength = {
  streak_weeks: number;
  weeks_hit: number;
  weeks_total: number;
  current_week_sessions: number;
};

export type Yoga = { sessions: number; per_week_avg: number };

export type Lifestyle = { strength: Strength; yoga: Yoga };

/** Espelho do `HealthSummaryOut` (backend/app/health/router.py). Séries
 * vazias -> bloco null; dose_response/lifestyle sempre presentes. */
export type HealthSummaryOut = {
  sleep: SleepBlock | null;
  hrv: HrvBlock | null;
  rhr: RhrBlock | null;
  stress: StressBlock | null;
  pmc: PmcBlock | null;
  dose_response: DoseResponse;
  lifestyle: Lifestyle;
};

/** Painel Saúde inteiro em 1 payload (HLT-02). Janela: seletor fixo do
 * painel (7/30/42/60/90d — feature health-window, default 60); o backend
 * valida `days` em [7, 365]. */
export async function getHealthSummary(days = 60): Promise<HealthSummaryOut> {
  const res = await fetch(`${API_BASE}/api/health/summary?days=${days}`, {
    cache: "no-store",
  });
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as HealthSummaryOut;
}
