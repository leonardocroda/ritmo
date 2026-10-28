"use client";

// Detalhe do treino (TRN-16/19/20/24/26/27): cabeçalho de métricas (cada
// uma omitida quando null no banco), faixa de contexto (só o que existir),
// tabela de consistência (Δ pace ao lado do drift cardíaco — AD-005) e
// estrutura. Sem splits → resumo + nota "sem voltas registradas", sem
// gráfico. 404 → "Treino não encontrado" + volta à lista. O gráfico de
// splits entra aqui na T12.

import { useEffect, useState, useRef } from "react";
import Link from "next/link";

import {
  getActivityDetail,
  getEvaluation,
  setActivityShoe,
  ApiError,
  type ActivityDetailOut,
  type EvaluationOut,
} from "@/lib/api";
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
import Skeleton from "@/components/Skeleton";
import EvaluateForm from "@/components/workouts/EvaluateForm";
import EvaluationCard, { EvaluationHistory } from "@/components/workouts/EvaluationCard";
import ShoePickerModal from "@/components/workouts/ShoePickerModal";

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
    <div className="rounded-card border border-border bg-card px-3 py-2">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="mt-0.5 text-sm font-medium tabular-nums">{value}</dd>
    </div>
  );
}

function Chip({ label, value }: { label: string; value: string }) {
  return (
    <span className="rounded-full border border-border bg-card px-3 py-1 text-sm tabular-nums">
      <span className="text-muted">{label}</span> {value}
    </span>
  );
}

function ConsistencyRow({ label, value }: { label: string; value: string }) {
  return (
    <tr className="border-t border-border first:border-t-0">
      <th scope="row" className="px-4 py-2 text-left text-sm font-normal text-muted">
        {label}
      </th>
      <td className="px-4 py-2 text-right text-sm font-medium tabular-nums">{value}</td>
    </tr>
  );
}

export default function WorkoutDetail({ id }: { id: number }) {
  // key={id} no server page remonta este componente por treino: o estado
  // inicial "loading" já cobre cada id novo (sem setState síncrono em effect).
  const [state, setState] = useState<DetailState>({ kind: "loading" });
  const [showShoeModal, setShowShoeModal] = useState(false);
  const modalShownRef = useRef(false);

  // Polling (~2s) enquanto existe avaliação pending (EVAL-25) — o worker
  // conclui em background; cada tick busca o status das pendentes e
  // mescla no estado local (done → card; error → motivo preservado).
  useEffect(() => {
    if (state.kind !== "ready") return;
    const pending = state.detail.evaluations.filter((e) => e.status === "pending");
    if (pending.length === 0) return;
    const activityId = state.detail.activity.id;
    const timer = setInterval(() => {
      pending.forEach((item) => {
        getEvaluation(activityId, item.id)
          .then((fresh) => {
            setState((prev) => {
              if (prev.kind !== "ready") return prev;
              return {
                ...prev,
                detail: {
                  ...prev.detail,
                  evaluations: prev.detail.evaluations.map((e) =>
                    e.id === fresh.id ? fresh : e,
                  ),
                  // Badge "Avaliado" acende quando o worker conclui (EVAL-20)
                  activity:
                    fresh.status === "done"
                      ? { ...prev.detail.activity, evaluated: true }
                      : prev.detail.activity,
                },
              };
            });
          })
          .catch(() => {
            // oscilação de rede: o próximo tick tenta de novo
          });
      });
    }, 2000);
    return () => clearInterval(timer);
  }, [state]);

  // Gatilho do modal de tênis: abre 1x por visita se for corrida sem tênis
  useEffect(() => {
    if (state.kind !== "ready") return;
    const { activity, shoe } = state.detail;
    const isRunning =
      activity.activity_type === "running" || activity.activity_type === "trail_running";
    
    if (isRunning && shoe === null && !modalShownRef.current) {
      modalShownRef.current = true;
      setShowShoeModal(true);
    }
  }, [state]);

  const handleShoeAssigned = async (shoe: { id: number; name: string; brand: string | null; model: string | null; status: string }) => {
    setShowShoeModal(false);
    // Refetch do detail para mostrar o badge
    try {
      const fresh = await getActivityDetail(id);
      setState({ kind: "ready", detail: fresh });
    } catch {
      // erro silencioso - o estado atual permanece
    }
  };

  const handleShoeDismissed = () => {
    setShowShoeModal(false);
  };

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

  // Avaliação pedida: prepend do pending no estado local (o badge
  // "Avaliado" acende quando o worker conclui — done — no polling;
  // EVAL-18/20)
  function handleEvaluated(evaluation: EvaluationOut) {
    setState((prev) =>
      prev.kind === "ready"
        ? {
            ...prev,
            detail: {
              ...prev.detail,
              evaluations: [evaluation, ...prev.detail.evaluations],
            },
          }
        : prev,
    );
  }

  if (state.kind === "loading") {
    // Skeleton no lugar do texto de carregamento (DSN-23): título +
    // cartão de gráfico + linhas de texto.
    return (
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-6 sm:px-6">
        <div className="space-y-3">
          <Skeleton className="h-5 w-1/3 rounded-ctl" />
          <Skeleton className="h-56 w-full rounded-card" />
          <Skeleton className="h-4 w-2/3 rounded-ctl" />
          <Skeleton className="h-4 w-1/2 rounded-ctl" />
        </div>
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
        <p className="rounded-card border border-border bg-card px-4 py-3 text-sm text-muted">
          Não foi possível carregar o treino: {state.message}
        </p>
      </main>
    );
  }

  const { activity, splits, consistency, context, evaluations, shoe } = state.detail;
  // Avaliação existe para corrida (EVAL-10): mesmo vocabulário do backend
  const isRunning =
    activity.activity_type === "running" || activity.activity_type === "trail_running";
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
          {shoe !== null && (
            <span className="rounded-full bg-accent/15 px-2 py-0.5 text-sm font-medium text-accent">
              {shoe.name}
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
          <div className="mt-2 overflow-hidden rounded-card border border-border bg-card">
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

      {/* Avaliar com IA (EVAL-01/10): só corridas têm formulário; a
          avaliação mais recente como card (pending → análise, error →
          motivo), anteriores no histórico; re-avaliação sempre por
          clique explícito (custo de tokens) */}
      {isRunning && (
        <>
          <EvaluateForm
            activity={activity}
            pending={evaluations.some((e) => e.status === "pending")}
            onEvaluated={handleEvaluated}
          />
          {evaluations.length > 0 && (
            <>
              <EvaluationCard evaluation={evaluations[0]} />
              <EvaluationHistory evaluations={evaluations.slice(1)} />
            </>
          )}
        </>
      )}

      {/* Voltas: sem splits → nota (sem gráfico); com splits → gráfico
          proporcional (T12) */}
      {splits.length === 0 && (
        <p className="mt-6 text-sm text-muted">sem voltas registradas</p>
      )}
      {splits.length > 0 && (
        <section className="mt-6">
          <h2 className="text-sm font-medium text-muted">Voltas</h2>
          <div className="mt-2 rounded-card border border-border bg-card p-3">
            <SplitsChart
              splits={splits}
              zones={state.detail.zones}
              hrColor={state.detail.hr_color}
            />
          </div>
        </section>
      )}

      {/* Modal de seleção de tênis (T10): abre 1x por visita para corrida sem tênis */}
      {showShoeModal && (
        <ShoePickerModal
          activityId={activity.id}
          inferredType={activity.inferred_type}
          onAssigned={handleShoeAssigned}
          onDismiss={handleShoeDismissed}
        />
      )}
    </main>
  );
}
