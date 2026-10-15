"use client";

// Detalhe do treino (TRN-16/19/20/24/26/27): cabeçalho de métricas (cada
// uma omitida quando null no banco), faixa de contexto (só o que existir),
// tabela de consistência (Δ pace ao lado do drift cardíaco — AD-005) e
// estrutura. Sem splits → resumo + nota "sem voltas registradas", sem
// gráfico. 404 → "Treino não encontrado" + volta à lista. O gráfico de
// splits entra aqui na T12.

import { useEffect, useState } from "react";
import Link from "next/link";

import { getActivityDetail, ApiError, type ActivityDetailOut } from "@/lib/api";
import {
  formatCadence,
  formatDateTime,
  formatDuration,
  formatInferredType,
  formatKm,
  formatPace,
  formatTemp,
} from "@/lib/format";
import SplitsChart from "@/components/workouts/SplitsChart";

type DetailState =
  | { kind: "loading" }
  | { kind: "not-found" }
  | { kind: "error"; message: string }
  | { kind: "ready"; detail: ActivityDetailOut };

/** Delta com sinal: 6 -> "+6", -2.04 -> "-2", vírgula quando tem decimal. */
function formatSigned(value: number, decimals = 0): string {
  const fixed = value.toFixed(decimals).replace(".", ",");
  return value > 0 ? `+${fixed}` : fixed;
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-card px-3 py-2">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="mt-0.5 text-sm font-medium">{value}</dd>
    </div>
  );
}

function Chip({ label, value }: { label: string; value: string }) {
  return (
    <span className="rounded-full border border-white/10 bg-card px-3 py-1 text-sm">
      <span className="text-muted">{label}</span> {value}
    </span>
  );
}

function ConsistencyRow({ label, value }: { label: string; value: string }) {
  return (
    <tr className="border-t border-white/10 first:border-t-0">
      <th scope="row" className="px-4 py-2 text-left text-sm font-normal text-muted">
        {label}
      </th>
      <td className="px-4 py-2 text-right text-sm font-medium">{value}</td>
    </tr>
  );
}

export default function WorkoutDetail({ id }: { id: number }) {
  // key={id} no server page remonta este componente por treino: o estado
  // inicial "loading" já cobre cada id novo (sem setState síncrono em effect).
  const [state, setState] = useState<DetailState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    getActivityDetail(id)
      .then((detail) => {
        if (!cancelled) setState({ kind: "ready", detail });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) {
          setState({ kind: "not-found" });
        } else {
          setState({
            kind: "error",
            message: err instanceof Error ? err.message : "Erro inesperado",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (state.kind === "loading") {
    return (
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-6 sm:px-6">
        <p className="text-sm text-muted">Carregando treino…</p>
      </main>
    );
  }

  if (state.kind === "not-found") {
    return (
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col items-center justify-center px-4 py-16 text-center sm:px-6">
        <h1 className="text-2xl font-semibold tracking-tight">
          Treino não encontrado
        </h1>
        <p className="mt-2 text-sm text-muted">
          O treino que você procura não existe ou ainda não foi sincronizado.
        </p>
        <Link
          href="/treinos"
          className="mt-6 rounded-full border border-accent/30 px-4 py-1.5 text-sm font-medium text-accent hover:bg-accent/10"
        >
          ← Voltar para a lista
        </Link>
      </main>
    );
  }

  if (state.kind === "error") {
    return (
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-6 sm:px-6">
        <p className="rounded-xl border border-white/10 bg-card px-4 py-3 text-sm text-muted">
          Não foi possível carregar o treino: {state.message}
        </p>
      </main>
    );
  }

  const { activity, splits, consistency, context } = state.detail;
  const hasContext =
    context.sleep !== null ||
    context.hrv !== null ||
    context.rhr !== null ||
    context.temperature_c !== undefined;

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-6 sm:px-6">
      <header>
        <p className="text-sm text-muted">{formatDateTime(activity.start_time)}</p>
        <h1 className="mt-0.5 text-2xl font-semibold tracking-tight">
          {activity.name ?? "Treino"}
        </h1>
        <p className="mt-2 flex flex-wrap items-center gap-2">
          {activity.inferred_type !== null && (
            <span className="rounded-full bg-accent/15 px-2 py-0.5 text-sm font-medium text-accent">
              {formatInferredType(activity.inferred_type)}
            </span>
          )}
          {activity.evaluated && (
            <span className="rounded-full bg-accent/15 px-2 py-0.5 text-sm font-medium text-accent">
              Avaliado
            </span>
          )}
        </p>
      </header>

      {/* Cabeçalho de métricas — cada uma omitida quando null (TRN-20) */}
      <dl className="mt-4 grid grid-cols-3 gap-2 sm:grid-cols-4">
        {activity.distance_m > 0 && (
          <Metric label="Distância" value={formatKm(activity.distance_m)} />
        )}
        <Metric label="Duração" value={formatDuration(activity.duration_s)} />
        {activity.pace_s !== null && (
          <Metric label="Pace" value={`${formatPace(activity.pace_s)}/km`} />
        )}
        {activity.avg_hr !== null && (
          <Metric label="FC média" value={`${activity.avg_hr} bpm`} />
        )}
        {activity.max_hr !== null && (
          <Metric label="FC máx" value={`${activity.max_hr} bpm`} />
        )}
        {activity.avg_cadence !== null && (
          <Metric label="Cadência" value={formatCadence(activity.avg_cadence)} />
        )}
        {activity.elevation_gain_m !== null && (
          <Metric
            label="Elevação"
            value={`${formatSigned(activity.elevation_gain_m)} m`}
          />
        )}
      </dl>

      {/* Estrutura derivada (P2) — só quando existe */}
      {activity.structure !== null && (
        <section className="mt-6">
          <h2 className="text-sm font-medium text-muted">Estrutura</h2>
          <p className="mt-2 text-sm">{activity.structure}</p>
        </section>
      )}

      {/* Faixa de contexto — só o que existir (TRN-26/27) */}
      {hasContext && (
        <section className="mt-6">
          <h2 className="text-sm font-medium text-muted">Contexto do dia</h2>
          <div className="mt-2 flex flex-wrap gap-2">
            {context.sleep !== null && (
              <Chip
                label="Sono"
                value={`${formatDuration(context.sleep.duration_s)}${context.sleep.score !== null ? ` · ${context.sleep.score}` : ""}`}
              />
            )}
            {context.hrv !== null && (
              <Chip
                label="HRV"
                value={`${Math.round(context.hrv.value)}${context.hrv.status !== null ? ` (${context.hrv.status})` : ""}`}
              />
            )}
            {context.rhr !== null && (
              <Chip label="FC repouso" value={`${context.rhr.value} bpm`} />
            )}
            {context.temperature_c !== undefined && (
              <Chip label="Temperatura" value={formatTemp(context.temperature_c)} />
            )}
          </div>
        </section>
      )}

      {/* Tabela de consistência (TRN-24): Δ pace junto do drift cardíaco;
          oculta quando consistency=null (<8km ou <4 voltas) */}
      {consistency !== null && (
        <section className="mt-6">
          <h2 className="text-sm font-medium text-muted">Consistência</h2>
          <div className="mt-2 overflow-hidden rounded-xl border border-white/10 bg-card">
            <table className="w-full">
              <tbody>
                {consistency.first_half_pace_s !== null && (
                  <ConsistencyRow
                    label="Pace 1ª metade"
                    value={`${formatPace(consistency.first_half_pace_s)}/km`}
                  />
                )}
                {consistency.second_half_pace_s !== null && (
                  <ConsistencyRow
                    label="Pace 2ª metade"
                    value={`${formatPace(consistency.second_half_pace_s)}/km`}
                  />
                )}
                {consistency.balance_delta_s !== null && (
                  <ConsistencyRow
                    label="Δ pace (1ª → 2ª)"
                    value={`${formatSigned(consistency.balance_delta_s)} s/km (${formatSigned(consistency.balance_delta_pct ?? 0, 1)}%)`}
                  />
                )}
                {consistency.hr_drift_bpm !== null && (
                  <ConsistencyRow
                    label="Drift cardíaco"
                    value={`${formatSigned(consistency.hr_drift_bpm)} bpm`}
                  />
                )}
                {consistency.decoupling_pct !== null && (
                  <ConsistencyRow
                    label="Decoupling FC/pace"
                    value={`${formatSigned(consistency.decoupling_pct, 1)}%`}
                  />
                )}
                {consistency.cadence_fade_spm !== undefined && (
                  <ConsistencyRow
                    label="Fade de cadência"
                    value={`${formatSigned(consistency.cadence_fade_spm)} spm`}
                  />
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Voltas: sem splits → nota (sem gráfico); com splits → gráfico
          proporcional (T12) */}
      {splits.length === 0 && (
        <p className="mt-6 text-sm text-muted">sem voltas registradas</p>
      )}
      {splits.length > 0 && (
        <section className="mt-6">
          <h2 className="text-sm font-medium text-muted">Voltas</h2>
          <div className="mt-2 rounded-xl border border-white/10 bg-card p-3">
            <SplitsChart
              splits={splits}
              zones={state.detail.zones}
              hrColor={state.detail.hr_color}
            />
          </div>
        </section>
      )}
    </main>
  );
}
