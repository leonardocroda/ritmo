// Cliente tipado da API — espelha os contratos do backend (designs do
// garmin-sync e workouts-list). A UI lê exclusivamente daqui, nunca do
// Garmin (AD-002): o sync polleia `JobOut` e os painéis leem o domínio
// de leitura `activities`.

// Auth (emenda UAT, 20/10 — AD-020): as chamadas vão pelo PRÓPRIO Next
// (rewrite same-origin em next.config.ts → BACKEND_URL). Base vazia =
// relativa: o cookie de sessão vale para o host que o usuário abriu e o
// proxy otimista o vê em qualquer um. CORS deixou de ser requisito.
export const API_BASE = "";

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
  const res = await apiFetch("/api/sync", { method: "POST" });
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as JobCreated;
}

/** Último job do usuário — o que a UI poleia a cada 2s (SYNC-05). */
export async function getLatestJob(): Promise<LatestJob> {
  const res = await apiFetch("/api/sync/jobs/latest", {
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

// ---- Avaliar com IA: contratos do design ai-evaluation ----

/** Vereditos do plano §9.2 — validados no backend antes de persistir. */
export type Verdict = "on_target" | "too_hard" | "too_easy" | "context_explained" | "fatigue_signal";

/** JSON de veredito §9.2 — o que a NIM devolve, já sanitizado pelo backend
 * (`pct_zona_alvo` é sempre o número calculado em Python — AD-003). */
export type VerdictJson = {
  veredito: Verdict;
  headline: string;
  execucao_vs_intencao: { pct_zona_alvo: number | null; principais_desvios: string[] };
  o_que_funcionou: string[];
  corrigir_prox_vez: string[];
  contexto_relevante: string[];
  confianca: "alta" | "média" | "baixa";
};

/** Espelho do `EvaluationOut` (backend/app/evaluation/schemas.py).
 * status: pending → done | error (emenda job 18/10) — o POST devolve
 * pending e a UI polla até o worker concluir. */
export type EvaluationOut = {
  id: number;
  activity_id: number;
  intent_type: InferredType;
  intent_text: string | null;
  verdict: Verdict;
  verdict_json: VerdictJson | null;
  model: string;
  prompt_version: string;
  tokens_in: number;
  tokens_out: number;
  status: "pending" | "done" | "error";
  error: string | null;
  created_at: string;
};

/** Corpo do POST de avaliação (EVAL-01/11): os 7 tipos 1:1 com InferredType. */
export type EvaluateRequest = {
  intent_type: InferredType;
  intent_text?: string;
};

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
  activity_type: string;
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

/** Espelho do `ActivityDetailOut` do detalhe (TRN-13/19/26/27 + EVAL-17). */
export type ActivityDetailOut = {
  activity: ActivityOut;
  splits: SplitOut[];
  zones: ZoneMeta[];
  hr_color: string;
  consistency: Consistency | null;
  context: ContextOut;
  evaluations: EvaluationOut[];
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
  const res = await apiFetch(`/api/activities${query ? `?${query}` : ""}`, {
    cache: "no-store",
  });
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as ActivityListOut;
}

/** Detalhe do treino (TRN-13). 404 = id inexistente (ApiError.status). */
export async function getActivityDetail(id: number): Promise<ActivityDetailOut> {
  const res = await apiFetch(`/api/activities/${id}`, {
    cache: "no-store",
  });
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as ActivityDetailOut;
}

/** Pede a avaliação do treino sob a intenção declarada (EVAL-21).
 * Job (emenda 18/10): responde 201 com o registro `pending` — a NIM
 * roda no worker; poll `getEvaluation` até done/error. Erros do
 * request: 404/422 (intenção), 503 (sem NVIDIA_API_KEY), 500 (zonas). */
export async function evaluateActivity(
  id: number,
  body: EvaluateRequest,
): Promise<EvaluationOut> {
  const res = await apiFetch(`/api/activities/${id}/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as EvaluationOut;
}

/** Status de uma avaliação para o polling da UI (EVAL-25). 404 = id
 * inexistente ou de outro treino. */
export async function getEvaluation(
  activityId: number,
  evaluationId: number,
): Promise<EvaluationOut> {
  const res = await apiFetch(
    `/api/activities/${activityId}/evaluate/${evaluationId}`,
    { cache: "no-store" },
  );
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as EvaluationOut;
}

// ---- Painel Performance (ex-Potencial): contratos do design potential-panel + panel-clarity ----

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

/** Espelho do `PotentialOut` (backend/app/potential/router.py) — com o
 * `pmc` de volta (AD-017 reverte a CLR-03): curva de carga com janela
 * fixa de 60d e sem query params. */
export type PotentialOut = {
  vdot: VdotBlock;
  predictions: Record<CanonicalEvent, PredictionRow>;
  vo2max: Vo2maxBlock | null;
  decay: DecayRow[];
  pmc: PmcBlock | null;
};

/** Painel Performance inteiro em 1 payload (POT-11) — sem query params:
 * o `days` segue morto (CLR-04: um `?days=` qualquer é ignorado pelo
 * backend) e o `pmc` voltou com janela fixa de 60d (AD-017). */
export async function getPotential(): Promise<PotentialOut> {
  const res = await apiFetch("/api/potential", {
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

/** Ponto da PMC (Painel Performance — AD-017 reverte a CLR-03) — null
 * espelha a linha do banco (janela 28d incompleta). */
export type PmcPoint = {
  date: string;
  ctl: number | null;
  atl: number | null;
  tsb: number | null;
  acwr: number | null;
};

/** Bloco Carga de treino (CLR-01) — contrato do Painel Performance
 * (AD-017 reverte a CLR-03: o bloco voltou do Saúde pra cá): janela
 * fixa de 60d; sem linhas em `load` -> null (CLR-02 — estado vazio,
 * não erro). */
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

/** Espelho do `HealthSummaryOut` (backend/app/health/router.py) — sem
 * `pmc`: a curva de carga voltou ao painel Performance (AD-017). Séries
 * vazias -> bloco null; dose_response/lifestyle sempre presentes. */
export type HealthSummaryOut = {
  sleep: SleepBlock | null;
  hrv: HrvBlock | null;
  rhr: RhrBlock | null;
  stress: StressBlock | null;
  dose_response: DoseResponse;
  lifestyle: Lifestyle;
};

/** Painel Saúde inteiro em 1 payload (HLT-02). Janela: seletor fixo do
 * painel (7/30/42/60/90d — feature health-window, default 60); o backend
 * valida `days` em [7, 365]. */
export async function getHealthSummary(days = 60): Promise<HealthSummaryOut> {
  const res = await apiFetch(`/api/health/summary?days=${days}`, {
    cache: "no-store",
  });
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as HealthSummaryOut;
}

// ---- Auth: contratos do design auth (feature auth) ----

/** Espelho do `MeOut` (backend/app/auth/schemas.py) — corpo de
 * register/login/me; nunca expõe password_hash. */
export type MeOut = {
  id: number;
  email: string | null;
  display_name: string;
};

/** Corpo do `POST /api/auth/register` — espelho do `RegisterIn`. */
export type RegisterInput = {
  display_name: string;
  email: string;
  password: string;
  invite_code: string;
};

/** Erro de auth: `ApiError` + erros por campo quando o backend responde
 * 422 (detail do FastAPI é a lista {loc, msg}) — a tela de registro
 * exibe cada mensagem junto do input correspondente. */
export class AuthError extends ApiError {
  fieldErrors: Record<string, string>;

  constructor(status: number, message: string, fieldErrors: Record<string, string> = {}) {
    super(status, message);
    this.fieldErrors = fieldErrors;
  }
}

/** Wrapper central de fetch (design auth): todo request sai com
 * `credentials: "include"` (cookie host-only da API) e 401 fora do fluxo
 * de auth redireciona para `/login?next=<rota corrente>` (AUTH-21) —
 * sessão expirou em uso. Guardas anti-loop: helpers de auth
 * (`/api/auth/*`) tratam o 401 como erro inline, e fetches feitos já
 * dentro de /login não redirecionam de novo. */
export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const res = await fetch(`${API_BASE}${path}`, { credentials: "include", ...init });
  if (
    res.status === 401 &&
    !path.startsWith("/api/auth/") &&
    !window.location.pathname.startsWith("/login")
  ) {
    window.location.replace(
      `/login?next=${encodeURIComponent(window.location.pathname + window.location.search)}`,
    );
  }
  return res;
}

/** Erro de auth a partir do corpo da API. String → mensagem única (401/403/
 * 409/429 em PT-BR); lista do 422 → mapeada por campo (`loc[1]`), com o
 * prefixo "Value error," do Pydantic removido. */
async function parseAuthError(res: Response): Promise<AuthError> {
  let message = `Erro HTTP ${res.status}`;
  const fieldErrors: Record<string, string> = {};
  try {
    const body: unknown = await res.json();
    const raw = (body as { detail?: unknown }).detail;
    if (typeof raw === "string") {
      message = raw;
    } else if (Array.isArray(raw)) {
      for (const item of raw) {
        const loc = (item as { loc?: unknown[] }).loc;
        const msg = (item as { msg?: unknown }).msg;
        if (typeof msg !== "string") continue;
        const field = loc?.length === 2 && typeof loc[1] === "string" ? loc[1] : "";
        if (field !== "" && !(field in fieldErrors)) {
          fieldErrors[field] = msg.replace(/^Value error,\s*/i, "");
        }
      }
      const first = Object.values(fieldErrors)[0];
      if (first !== undefined) message = first;
    } else if (raw != null) {
      message = JSON.stringify(raw);
    }
  } catch {
    // resposta sem corpo JSON — o status já é a mensagem
  }
  return new AuthError(res.status, message, fieldErrors);
}

/** Cadastro por convite + auto-login (AUTH-01). 201 = conta criada com
 * cookie de sessão; 403 registro desabilitado/código inválido, 409 email
 * já cadastrado, 422 por campo (AuthError.fieldErrors). */
export async function register(payload: RegisterInput): Promise<MeOut> {
  const res = await apiFetch("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw await parseAuthError(res);
  return (await res.json()) as MeOut;
}

/** Login email+senha (AUTH-06/07/08). 200 + cookie; 401 genérica única;
 * 429 no lockout de 5 falhas/15min — mensagem acionável do backend. */
export async function login(email: string, password: string): Promise<MeOut> {
  const res = await apiFetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw await parseAuthError(res);
  return (await res.json()) as MeOut;
}

/** Logout (AUTH-09): revoga a sessão corrente e limpa o cookie (204). */
export async function logout(): Promise<void> {
  const res = await apiFetch("/api/auth/logout", { method: "POST" });
  if (!res.ok) throw await parseAuthError(res);
}

/** Quem está logado (AUTH-10). 200 {id, email, display_name}; 401 = sem
 * sessão (UserMenu simplesmente não renderiza — AUTH-23). */
export async function me(): Promise<MeOut> {
  const res = await apiFetch("/api/auth/me");
  if (!res.ok) throw await parseAuthError(res);
  return (await res.json()) as MeOut;
}

// ---- Perfil: zonas de FC (feature hr-zones) ----

/** Métodos de cálculo (HRZ-08) — chaves ASCII da API, rótulo na UI. */
export type HrZoneMethod = "lthr" | "fcr" | "fcmax";

/** Percentuais de uma zona em pontos — high null = Z5 aberta no lthr. */
export type HrZoneBound = { low: number; high: number | null };

/** Espelho do `MetricOut` — valor vigente com fonte e vigência
 * (HRZ-01); null quando nunca configurado. */
export type HrMetric = {
  value: number;
  source: string;
  valid_from: string;
};

/** Espelho do `ConfigOut` — método e percentuais vigentes (HRZ-12).
 * `method` é sempre um dos 3: toda escrita valida contra Literal. */
export type HrZoneConfig = {
  method: HrZoneMethod;
  bounds: { zones: HrZoneBound[] };
  valid_from: string;
};

/** Zona derivada em bpm (HRZ-10) — high null = Z5 aberta do lthr. */
export type HrZone = { n: number; low: number; high: number | null };

/** Espelho do `HrZonesOut` (GET e resposta do PUT): métricas vigentes
 * por kind, preferência de posse por kind (HRZ-20/21/22 — `garmin` =
 * o sync manda; `manual` = edição vence), config, zonas derivadas em
 * bpm (null sem config ou sem a métrica exigida — HRZ-11, estado vazio
 * honesto) e os defaults dos 3 métodos para prefill (HRZ-08). */
export type HrZonesOut = {
  metrics: Record<"fcmax" | "fcrest" | "fclthr", HrMetric | null>;
  modes: Record<"fcmax" | "fcrest" | "fclthr", "garmin" | "manual">;
  config: HrZoneConfig | null;
  zones: HrZone[] | null;
  defaults: Record<HrZoneMethod, HrZoneBound[]>;
};

/** Corpo do PUT (HRZ-02/08/09 + HRZ-20/21): métricas e/ou método e/ou
 * bounds e/ou preferências de posse — método sem bounds aplica os
 * defaults; bounds sem método herdam o método vigente; `sync_modes`
 * com "garmin" devolve a métrica ao sync (o próximo sync reassume). */
export type HrZonesUpdate = {
  metrics?: { fcmax?: number; fcrest?: number; fclthr?: number };
  method?: HrZoneMethod;
  bounds?: { zones: HrZoneBound[] };
  sync_modes?: Partial<Record<"fcmax" | "fcrest" | "fclthr", "garmin" | "manual">>;
};

/** Linha do histórico de métricas (HRZ-15) — DESC por (valid_from, id). */
export type HrMetricHistory = {
  kind: "fcmax" | "fcrest" | "fclthr";
  value: number;
  source: string;
  valid_from: string;
};

/** Linha do histórico de configs (HRZ-15) — configs não têm fonte. */
export type HrConfigHistory = {
  method: HrZoneMethod;
  bounds: { zones: HrZoneBound[] };
  valid_from: string;
};

/** Espelho do `HrZonesHistoryOut` — as duas séries já vêm DESC. */
export type HrZonesHistory = {
  metrics: HrMetricHistory[];
  configs: HrConfigHistory[];
};

/** Zonas vigentes hoje (HRZ-01/10/11) — métricas, config, zonas em
 * bpm e defaults para prefill. */
export async function getHrZones(): Promise<HrZonesOut> {
  const res = await apiFetch("/api/profile/hr-zones", {
    cache: "no-store",
  });
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as HrZonesOut;
}

/** A única escrita (HRZ-02/03/04/08/09): métricas e/ou método e/ou
 * bounds, resposta no shape do GET — a UI re-renderiza da resposta.
 * 422 aponta campo ou zona com motivo PT-BR (HRZ-14). */
export async function updateHrZones(payload: HrZonesUpdate): Promise<HrZonesOut> {
  const res = await apiFetch("/api/profile/hr-zones", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as HrZonesOut;
}

/** Histórico de métricas e configs (HRZ-15), mais recente primeiro. */
export async function getHrZonesHistory(): Promise<HrZonesHistory> {
  const res = await apiFetch("/api/profile/hr-zones/history", {
    cache: "no-store",
  });
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as HrZonesHistory;
}
