// Cliente tipado da API de sync — espelha o contrato do backend
// (`JobOut`/`stats_json` do design do garmin-sync). A UI lê progresso
// exclusivamente daqui (polling de 2s), nunca do Garmin (AD-002).

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

async function parseError(res: Response): Promise<Error> {
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
  return new Error(detail);
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
