"use client";

// SyncButton — o botão "Puxar do Garmin" (SYNC-08/26).
// Estados: idle → running (disabled + stats.message) → done (resumo
// PT-BR dos contadores) | error (mensagem) | reauth ("Reconectar
// Garmin" + instrução da CLI no lugar do resumo). O progresso vem
// exclusivamente do polling de 2s em GET /jobs/latest (AD-002).

import { useEffect, useState } from "react";

import { getLatestJob, startSync, type JobOut, type SyncStats } from "@/lib/api";

const POLL_MS = 2000;

function plural(n: number, one: string, many: string): string {
  return n === 1 ? one : many;
}

/** Resumo PT-BR dos contadores finais do job (SYNC-06). */
function summarize(stats: SyncStats): string {
  return [
    `${stats.activities_new} ${plural(stats.activities_new, "atividade nova", "atividades novas")}`,
    `${stats.activities_updated} ${plural(stats.activities_updated, "atualizada", "atualizadas")}`,
    `${stats.splits} ${plural(stats.splits, "split", "splits")}`,
    `${stats.sleep_days} ${plural(stats.sleep_days, "noite de sono", "noites de sono")}`,
    `${stats.hrv_days} ${plural(stats.hrv_days, "dia de HRV", "dias de HRV")}`,
    `${stats.rhr_days} ${plural(stats.rhr_days, "dia de RHR", "dias de RHR")}`,
    `${stats.battery_days} ${plural(stats.battery_days, "dia de body battery", "dias de body battery")}`,
    `${stats.stress_days} ${plural(stats.stress_days, "dia de stress", "dias de stress")}`,
    `${stats.records} ${plural(stats.records, "recorde", "recordes")}`,
  ].join(" · ");
}

export default function SyncButton() {
  const [job, setJob] = useState<JobOut | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  const active = job !== null && (job.status === "pending" || job.status === "running");
  const stats = job?.stats ?? null;
  const reauth = job?.status === "error" && (stats?.reauth_needed ?? false);

  // Ao montar: busca a última sync — job ativo nasce desabilitado mesmo
  // depois de um refresh de página (SYNC-08).
  useEffect(() => {
    getLatestJob()
      .then(({ job: latest }) => setJob(latest))
      .catch(() => {
        // backend fora no load: botão segue idle e o clique mostra o erro
      });
  }, []);

  // Polling de 2s enquanto o job está ativo; para em estado final e
  // retoma quando um novo clique ativa um job de novo (SYNC-05).
  useEffect(() => {
    if (!active) return;
    const timer = setInterval(() => {
      getLatestJob()
        .then(({ job: latest }) => setJob(latest))
        .catch(() => {
          // oscilação de rede: o próximo tick tenta de novo
        });
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [active]);

  async function handleSync() {
    setFailure(null);
    try {
      await startSync(); // 201 = job criado; 409 cai no refresh abaixo
    } catch {
      // job ativo em outra aba ou backend fora — o refresh converge
    }
    try {
      const { job: latest } = await getLatestJob();
      setJob(latest);
    } catch {
      setFailure("Não foi possível iniciar o sync. Confira o backend e tente de novo.");
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        type="button"
        onClick={handleSync}
        disabled={active}
        className={
          active
            ? "rounded-full border border-border bg-card px-4 py-1.5 text-sm font-medium text-muted"
            : "rounded-full border border-accent/30 px-4 py-1.5 text-sm font-medium text-accent hover:bg-accent/10"
        }
      >
        {active ? (stats?.message ?? "Iniciando sync…") : "Puxar do Garmin"}
      </button>

      {failure !== null && (
        <p className="max-w-xs text-right text-xs text-muted">{failure}</p>
      )}

      {/* SYNC-26: "Reconectar Garmin" + CLI no lugar do resumo */}
      {reauth && (
        <p className="max-w-xs text-right text-xs text-muted">
          Reconectar Garmin: rode{" "}
          <code className="font-mono text-foreground">python -m app.garmin.login</code>{" "}
          e clique de novo.
        </p>
      )}

      {job?.status === "error" && !reauth && (
        <p className="max-w-xs text-right text-xs text-muted">{job.error}</p>
      )}

      {job?.status === "done" && stats !== null && (
        <div className="max-w-xs text-right text-xs text-muted">
          <p>{summarize(stats)}</p>
          {stats.warnings.map((warning) => (
            <p key={warning.tipo}>
              Aviso ({warning.tipo}): {warning.erro}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
