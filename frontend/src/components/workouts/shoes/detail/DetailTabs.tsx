"use client";

import Skeleton from "@/components/Skeleton";
import { Shoe, AnalysisShoeProfile, DegradationOut, DegradationSignal } from "@/lib/api";
import { getWorkoutTypeInfo, getZoneColor, compareWorkoutTypes } from "@/lib/shoes/workoutTypeLabels";
import { getSignalInfo, getDirection, getDirectionColor, getDirectionBg } from "@/lib/shoes/signalLabels";
import { formatKm, formatPace } from "@/lib/format";

type ViewMode = "overview" | "degradation";

interface EnrichedSignal extends DegradationSignal {
  label: string;
  tooltip: string;
  higherIsWorse: boolean;
  direction: "piorou" | "melhorou" | "estável";
  directionColor: string;
  directionBg: string;
}

interface DetailTabsProps {
  activeView: ViewMode;
  onChange: (v: ViewMode) => void;
  shoe: Shoe;
  profile: AnalysisShoeProfile | undefined;
  degradation: DegradationOut | null;
  enrichedSignals: EnrichedSignal[];
  degradationLoading: boolean;
  degradationError: string | null;
  analysisLoading: boolean;
  analysisError: string | null;
}

const TABS: { id: ViewMode; label: string }[] = [
  { id: "overview", label: "Visão Geral" },
  { id: "degradation", label: "Degradação" },
];

export function DetailTabs({
  activeView,
  onChange,
  shoe,
  profile,
  degradation,
  enrichedSignals,
  degradationLoading,
  degradationError,
  analysisLoading,
  analysisError,
}: DetailTabsProps) {
  // Compute aggregated group count for badge
  const aggregatedCount = profile
    ? Array.from(
        new Map(
          profile.groups
            .filter(g => g.n_corridas > 0)
            .map(g => [g.tipo, g])
        ).values()
      ).length
    : 0;

  const tabBadges = {
    overview: aggregatedCount,
    degradation: degradation?.signals?.length ?? 0,
  };

  return (
    <div className="space-y-4">
      {/* Tab bar */}
      <div className="flex gap-1 bg-raised/50 rounded-ctl p-1">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => onChange(t.id)}
            className={`flex-1 rounded-ctl px-4 py-2 text-sm font-medium transition-colors flex items-center justify-center gap-1.5 ${
              activeView === t.id
                ? "bg-lime/15 text-lime"
                : "text-muted hover:text-text"
            }`}
          >
            {t.label}
            {tabBadges[t.id] && tabBadges[t.id]! > 0 && (
              <span className="inline-flex items-center justify-center min-w-[1.25rem] h-5 rounded-full px-1.5 text-[10px] font-medium bg-lime/20 text-lime">
                {tabBadges[t.id]}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      {activeView === "overview" && (
        <OverviewSection
          shoe={shoe}
          profile={profile}
          loading={analysisLoading}
          error={analysisError}
        />
      )}

      {activeView === "degradation" && (
        <DegradationSection
          shoe={shoe}
          degradation={degradation}
          enrichedSignals={enrichedSignals}
          loading={degradationLoading}
          error={degradationError}
        />
      )}
    </div>
  );
}

// Overview Section
function OverviewSection({
  shoe,
  profile,
  loading,
  error,
}: {
  shoe: Shoe;
  profile: AnalysisShoeProfile | undefined;
  loading: boolean;
  error: string | null;
}) {
  if (loading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-12 w-full rounded-card" />
        <Skeleton className="h-12 w-full rounded-card" />
        <Skeleton className="h-12 w-full rounded-card" />
        <Skeleton className="h-12 w-full rounded-card" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-card border border-destructive/30 bg-destructive/10 p-4">
        <p className="text-sm text-destructive">{error}</p>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="rounded-card border border-border bg-card p-6 text-center">
        <p className="text-muted">Sem dados de análise para "{shoe.name}".</p>
      </div>
    );
  }

  // Aggregate by workout type (tipo) - backend returns multiple groups per tipo (one per pace band)
  const aggregated = new Map<string, {
    tipo: string;
    n_corridas: number;
    km_totais: number;
    pace_sum: number;
    pace_count: number;
    fc_sum: number;
    fc_count: number;
    cadencia_sum: number;
    cadencia_count: number;
  }>();

  for (const g of profile.groups) {
    if (g.n_corridas === 0) continue;
    const existing = aggregated.get(g.tipo);
    if (existing) {
      existing.n_corridas += g.n_corridas;
      existing.km_totais += g.km_totais;
      if (g.pace_medio_s != null) {
        existing.pace_sum += g.pace_medio_s * g.n_corridas;
        existing.pace_count += g.n_corridas;
      }
      if (g.fc_media != null) {
        existing.fc_sum += g.fc_media * g.n_corridas;
        existing.fc_count += g.n_corridas;
      }
      if (g.cadencia_media != null) {
        existing.cadencia_sum += g.cadencia_media * g.n_corridas;
        existing.cadencia_count += g.n_corridas;
      }
    } else {
      aggregated.set(g.tipo, {
        tipo: g.tipo,
        n_corridas: g.n_corridas,
        km_totais: g.km_totais,
        pace_sum: g.pace_medio_s != null ? g.pace_medio_s * g.n_corridas : 0,
        pace_count: g.pace_medio_s != null ? g.n_corridas : 0,
        fc_sum: g.fc_media != null ? g.fc_media * g.n_corridas : 0,
        fc_count: g.fc_media != null ? g.n_corridas : 0,
        cadencia_sum: g.cadencia_media != null ? g.cadencia_media * g.n_corridas : 0,
        cadencia_count: g.cadencia_media != null ? g.n_corridas : 0,
      });
    }
  }

  const aggregatedGroups = Array.from(aggregated.values())
    .sort((a, b) => compareWorkoutTypes(a.tipo, b.tipo))
    .map(a => ({
      tipo: a.tipo,
      banda: "agregado", // dummy field to satisfy AnalysisGroup type
      n_corridas: a.n_corridas,
      km_totais: a.km_totais,
      pace_medio_s: a.pace_count > 0 ? a.pace_sum / a.pace_count : null,
      fc_media: a.fc_count > 0 ? a.fc_sum / a.fc_count : null,
      cadencia_media: a.cadencia_count > 0 ? a.cadencia_sum / a.cadencia_count : null,
    }));

  if (aggregatedGroups.length === 0) {
    return (
      <div className="rounded-card border border-border bg-card p-8 text-center">
        <p className="font-medium mb-1">Nenhuma corrida associada a "{shoe.name}"</p>
        <p className="text-sm text-muted mb-4">Associe corridas na tela de Treinos para ver o perfil deste tênis.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        {aggregatedGroups.map((group, idx) => (
          <WorkoutTypeCard key={`${group.tipo}-${idx}`} group={group} />
        ))}
      </div>
    </div>
  );
}

// Degradation Section
function DegradationSection({
  shoe,
  degradation,
  enrichedSignals,
  loading,
  error,
}: {
  shoe: Shoe;
  degradation: DegradationOut | null;
  enrichedSignals: EnrichedSignal[];
  loading: boolean;
  error: string | null;
}) {
  if (loading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-12 w-full rounded-card" />
        <Skeleton className="h-12 w-full rounded-card" />
        <Skeleton className="h-12 w-full rounded-card" />
        <Skeleton className="h-12 w-full rounded-card" />
        <Skeleton className="h-12 w-full rounded-card" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-card border border-destructive/30 bg-destructive/10 p-4">
        <p className="text-sm text-destructive">{error}</p>
      </div>
    );
  }

  if (!degradation) {
    return <p className="text-sm text-muted text-center py-4">Sem dados de degradação.</p>;
  }

  const hasSignals = degradation.signals && degradation.signals.length > 0;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <h3 className="font-semibold">{shoe.name}</h3>
        <div className="flex items-center gap-2 text-sm text-muted num">
          <span>{degradation.total_km.toFixed(1)} km total</span>
          <span>·</span>
          <span>{degradation.initial_runs ?? 0} corridas (inicial)</span>
          <span>·</span>
          <span>{degradation.final_runs ?? 0} corridas (final)</span>
        </div>
      </div>

      {/* Status badge */}
      <div className="mb-4">
        {degradation.insufficient ? (
          <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium bg-amber/15 text-amber border border-amber/30">
            <span className="w-1.5 h-1.5 rounded-full bg-amber" />
            Dados insuficientes
          </span>
        ) : (
          <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium bg-lime/15 text-lime border border-lime/30">
            <span className="w-1.5 h-1.5 rounded-full bg-lime" />
            Dados suficientes
          </span>
        )}
      </div>

      {/* Content */}
      {degradation.insufficient ? (
        <DegradationEmptyStates variant="insufficient" currentKm={degradation.total_km} />
      ) : !hasSignals ? (
        <DegradationEmptyStates variant="noSignals" />
      ) : (
        <>
          <DegradationTable signals={enrichedSignals} />
          <p className="text-xs text-muted text-center mt-2">
            Sinais, não veredito — esta análise não recomenda aposentadoria.
          </p>
        </>
      )}
    </div>
  );
}

// WorkoutTypeCard
function WorkoutTypeCard({ group }: { group: AnalysisShoeProfile["groups"][0] }) {
  const info = getWorkoutTypeInfo(group.tipo);
  const zoneColor = getZoneColor(info.zoneKey);

  return (
    <div
      className="rounded-card border border-border bg-card p-4 hover:border-border-hover hover:bg-raised/30 transition-colors"
      style={{ borderLeft: `4px solid ${zoneColor}` }}
    >
      <div className="flex items-center justify-between gap-2 flex-wrap mb-2">
        <span className="font-medium text-sm">{info.label}</span>
        <span
          className="rounded-full px-2 py-0.5 text-[10px] font-medium text-white"
          style={{ backgroundColor: zoneColor }}
        >
          {info.zoneLabel}
        </span>
      </div>

      <div className="mb-2 flex items-center gap-3 text-xs text-muted num">
        <span>{group.n_corridas} {group.n_corridas === 1 ? "corrida" : "corridas"}</span>
        <span>·</span>
        <span>{group.km_totais.toFixed(1)} km</span>
      </div>

      <div className="grid grid-cols-3 gap-2 text-sm">
        <div className="rounded-ctl bg-night/50 p-2 text-center">
          <div className="text-muted text-xs">pace médio</div>
          <div className="font-medium num text-text">
            {group.pace_medio_s ? formatPace(group.pace_medio_s) + "/km" : "—"}
          </div>
        </div>
        <div className="rounded-ctl bg-night/50 p-2 text-center">
          <div className="text-muted text-xs">fc média</div>
          <div className="font-medium num text-text">
            {group.fc_media ? group.fc_media.toFixed(0) + " bpm" : "—"}
          </div>
        </div>
        <div className="rounded-ctl bg-night/50 p-2 text-center">
          <div className="text-muted text-xs">cadência</div>
          <div className="font-medium num text-text">
            {group.cadencia_media ? group.cadencia_media.toFixed(0) + " spm" : "—"}
          </div>
        </div>
      </div>
    </div>
  );
}

// DegradationEmptyStates
function DegradationEmptyStates({ variant, currentKm = 0 }: { variant: "insufficient" | "noSignals"; currentKm?: number }) {
  if (variant === "insufficient") {
    return (
      <div className="rounded-lg border border-border bg-raised/30 p-6 text-center">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-amber/15 text-amber mb-3">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        </div>
        <p className="font-medium">Dados insuficientes para degradação</p>
        <p className="text-sm text-muted mt-1">
          Mínimo ~150 km acumulados para análise (tem {currentKm.toFixed(1)} km).
          Continue correndo com este tênis para ver sinais de degradação.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border bg-raised/30 p-6 text-center">
      <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-lime/15 text-lime mb-3">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
          <polyline points="22 4 12 14.01 9 11.01" />
        </svg>
      </div>
      <p className="font-medium">Nenhum sinal de degradação detectado</p>
      <p className="text-xs text-muted mt-1">O tênis mantém comportamento estável nas métricas analisadas.</p>
    </div>
  );
}

// DegradationTable
function DegradationTable({ signals }: { signals: EnrichedSignal[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-night/50 text-left">
            <th className="px-3 py-2 font-medium text-muted">Sinal</th>
            <th className="px-3 py-2 font-medium text-muted text-center">Inicial</th>
            <th className="px-3 py-2 font-medium text-muted text-center">Final</th>
            <th className="px-3 py-2 font-medium text-muted text-center">Δ</th>
            <th className="px-3 py-2 font-medium text-muted text-center">Direção</th>
            <th className="px-3 py-2 font-medium text-muted text-center">Conf.</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {signals.map((signal, idx) => (
            <tr key={idx} className="hover:bg-raised/50 transition-colors">
              <td className="px-3 py-2 font-medium text-text">{signal.label}</td>
              <td className="px-3 py-2 text-center num text-text">
                {signal.inicial.toFixed(signal.unidade === "EF" ? 4 : 1)} {signal.unidade}
              </td>
              <td className="px-3 py-2 text-center num text-text">
                {signal.final.toFixed(signal.unidade === "EF" ? 4 : 1)} {signal.unidade}
              </td>
              <td className="px-3 py-2 text-center num font-medium">
                {signal.delta !== 0 ? (
                  <span className={signal.directionColor}>
                    {signal.delta > 0 ? "+" : ""}{signal.delta.toFixed(signal.unidade === "EF" ? 4 : 1)} {signal.unidade}
                  </span>
                ) : (
                  <span className="text-muted">—</span>
                )}
              </td>
              <td className="px-3 py-2 text-center">
                <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${signal.directionBg}`}>
                  {signal.direction}
                </span>
              </td>
              <td className="px-3 py-2 text-center">
                <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium bg-border text-muted">
                  {signal.confianca}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}