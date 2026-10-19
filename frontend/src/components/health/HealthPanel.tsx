"use client";

// Painel Saúde (§4.5) — página-composição: busca /api/health/summary em 1
// round-trip POR JANELA (seletor fixo 7/30/42/60/90d — feature
// health-window, default 60) e monta as 4 seções do fio condutor
// (panel-clarity): Sono → Recuperação → Dose-resposta → Equilíbrio de
// vida, cada uma com cabeçalho forte numerado
// (PanelSection — CLR-12/13) e a linha-guia conectando tudo no topo
// (CLR-26). Sem PMC: a curva de carga voltou ao painel Performance
// (AD-017 reverte a CLR-03 — o bloco mudou de endpoint junto com a
// tela, AD-009). Bloco null -> estado vazio próprio do bloco (HLT-19);
// painel inteiro vazio (sono, HRV, RHR e estresse ausentes) -> estado
// vazio apontando o sync (CLR-11). A troca de janela refaz a busca
// mantendo os dados anteriores na tela; o seq descarta a resposta
// velha quando o usuário troca rápido (padrão WorkoutsList).

import { useEffect, useRef, useState, type ReactNode } from "react";

import { getHealthSummary, type HealthSummaryOut } from "@/lib/api";
import PanelSection from "@/components/PanelSection";
import DoseResponse from "@/components/health/DoseResponse";
import HrvChart from "@/components/health/HrvChart";
import HrvTable from "@/components/health/HrvTable";
import Lifestyle from "@/components/health/Lifestyle";
import RemChart from "@/components/health/RemChart";
import RhrChart from "@/components/health/RhrChart";
import SleepChart from "@/components/health/SleepChart";
import SleepStagesChart from "@/components/health/SleepStagesChart";
import StressChart from "@/components/health/StressChart";
import WeekdayPattern from "@/components/health/WeekdayPattern";

// Janelas fixas do seletor (spec health-window): semana aguda (7d — ATL),
// mês (30d — WHOOP M), fitness (42d — constante do CTL do TrainingPeaks),
// banda de HRV (60d — AD-010) e visão longa (90d).
const WINDOW_OPTIONS = [7, 30, 42, 60, 90] as const;
type WindowDays = (typeof WINDOW_OPTIONS)[number];

type PanelState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | {
      kind: "ready";
      panel: HealthSummaryOut;
      refreshing: boolean;
      refreshError: string | null;
    };

/** Estado vazio de um bloco — orienta o primeiro sync, sem erro (HLT-19). */
function BlockEmpty({ children }: { children: ReactNode }) {
  return (
    <p className="rounded-xl border border-white/10 bg-card px-4 py-6 text-sm text-muted">
      {children}
    </p>
  );
}

/** Seletor fixo de janela (HWF-01) — pill pattern do WorkoutsList. */
function WindowFilter({
  days,
  onSelect,
}: {
  days: WindowDays;
  onSelect: (days: WindowDays) => void;
}) {
  return (
    <div
      className="flex flex-wrap items-center gap-2"
      role="group"
      aria-label="Janela de tempo"
    >
      {WINDOW_OPTIONS.map((option) => {
        const active = option === days;
        return (
          <button
            key={option}
            type="button"
            aria-pressed={active}
            onClick={() => onSelect(option)}
            className={
              active
                ? "rounded-full bg-accent/15 px-3 py-1 text-sm font-medium text-accent"
                : "rounded-full px-3 py-1 text-sm text-muted hover:text-foreground"
            }
          >
            {option}d
          </button>
        );
      })}
    </div>
  );
}

export default function HealthPanel() {
  const [days, setDays] = useState<WindowDays>(60);
  const [state, setState] = useState<PanelState>({ kind: "loading" });
  const requestSeq = useRef(0);

  // Busca (re)feita por janela (HWF-02); o seq descarta a resposta velha
  // quando o usuário troca rápido (HWF-05 — padrão WorkoutsList). Erro no
  // refetch mantém os dados anteriores na tela com a mensagem junto ao
  // filtro (HWF-06); erro na primeira carga segue o fluxo existente.
  useEffect(() => {
    const seq = ++requestSeq.current;
    getHealthSummary(days)
      .then((panel) => {
        if (seq !== requestSeq.current) return;
        setState({
          kind: "ready",
          panel,
          refreshing: false,
          refreshError: null,
        });
      })
      .catch((err: unknown) => {
        if (seq !== requestSeq.current) return;
        const message = err instanceof Error ? err.message : "Erro inesperado";
        setState((prev) =>
          prev.kind === "ready"
            ? { ...prev, refreshing: false, refreshError: message }
            : { kind: "error", message },
        );
      });
  }, [days]);

  // Troca de janela no handler (regra react-hooks/set-state-in-effect):
  // mantém os dados atuais visíveis (HWF-04) e o effect busca a nova.
  function changeWindow(next: WindowDays) {
    if (next === days) return;
    setDays(next);
    setState((prev) =>
      prev.kind === "ready"
        ? { ...prev, refreshing: true, refreshError: null }
        : prev,
    );
  }

  if (state.kind === "loading") {
    return <p className="mt-6 text-sm text-muted">Carregando saúde…</p>;
  }

  if (state.kind === "error") {
    return (
      <p className="mt-6 rounded-xl border border-white/10 bg-card px-4 py-3 text-sm text-muted">
        Não foi possível carregar a saúde: {state.message}
      </p>
    );
  }

  const { sleep, hrv, rhr, stress, dose_response, lifestyle } = state.panel;

  // Estado vazio geral (CLR-11, sem o pmc — AD-017): painel vazio com
  // sono, HRV, RHR e estresse ausentes; a curva de carga mora no painel
  // Performance agora.
  if (sleep === null && hrv === null && rhr === null && stress === null) {
    return (
      <p className="mt-6 rounded-xl border border-white/10 bg-card px-4 py-6 text-sm text-muted">
        Nada por aqui ainda. Use o botão &ldquo;Puxar do Garmin&rdquo; no topo
        para sincronizar seus dados.
      </p>
    );
  }

  return (
    <div className="mt-4">
      {/* Seletor de janela (HWF-01): aplica a todas as seções */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <WindowFilter days={days} onSelect={changeWindow} />
        {state.refreshing && (
          <span className="text-sm text-muted">atualizando…</span>
        )}
      </div>
      {state.refreshError !== null && (
        <p className="mt-2 rounded-xl border border-white/10 bg-card px-3 py-2 text-sm text-muted">
          Não foi possível atualizar a janela: {state.refreshError}
        </p>
      )}

      {/* Linha-guia (CLR-26): o fio que conecta as 4 seções */}
      <p className="mt-3 text-sm text-muted">
        O fio: o sono recupera, o corpo responde, dormir mal custa — e a
        vida fora da corrida sustenta tudo.
      </p>

      <PanelSection
        index={1}
        title="Sono"
        subtitle="Durmo o suficiente pra absorver o treino? Duração de cada noite contra o piso de 7h, fases do sono, REM na banda de 21–31% e o padrão da semana."
      >
        {sleep !== null ? (
          <div className="space-y-3">
            <div className="rounded-xl border border-white/10 bg-card p-3">
              <SleepChart sleep={sleep} />
            </div>
            <div className="rounded-xl border border-white/10 bg-card p-3">
              <SleepStagesChart sleep={sleep} />
            </div>
            <div className="rounded-xl border border-white/10 bg-card p-3">
              <RemChart sleep={sleep} />
            </div>
            <div className="rounded-xl border border-white/10 bg-card p-3">
              <WeekdayPattern sleep={sleep} />
            </div>
          </div>
        ) : (
          <BlockEmpty>
            Sem dados de sono ainda — eles chegam no primeiro sync do Garmin.
          </BlockEmpty>
        )}
      </PanelSection>

      <PanelSection
        index={2}
        title="Recuperação"
        subtitle="Como o corpo está respondendo? HRV noturna e frequência cardíaca de repouso — os sinais diários de quanto da carga está virando adaptação."
      >
        <div className="space-y-3">
          {hrv !== null ? (
            <div className="rounded-xl border border-white/10 bg-card p-3">
              <HrvChart hrv={hrv} />
              {/* Valores diários com paginação (hrv-baseline, HRV-10..12);
                  remount por janela reseta a página (HWF-07) */}
              <HrvTable key={days} hrv={hrv} />
            </div>
          ) : (
            <BlockEmpty>
              Sem dados de HRV noturna ainda — eles chegam no primeiro sync do
              Garmin.
            </BlockEmpty>
          )}
          {rhr !== null ? (
            <div className="rounded-xl border border-white/10 bg-card p-3">
              <RhrChart rhr={rhr} />
            </div>
          ) : (
            <BlockEmpty>
              Sem dados de frequência cardíaca em repouso ainda — eles chegam
              no primeiro sync do Garmin.
            </BlockEmpty>
          )}
        </div>
      </PanelSection>

      <PanelSection
        index={3}
        title="Dose-resposta"
        subtitle="O que dormir mal me custa? Noites curtas (<6h) contra noites adequadas (≥6h45) — HRV e score médios da mesma noite mostram o preço."
      >
        <DoseResponse dose={dose_response} />
      </PanelSection>

      <PanelSection
        index={4}
        title="Equilíbrio de vida"
        subtitle="A base fora da corrida sustenta o treino? Força por semana, yoga e estresse médio da janela — o que apoia ou sabota a recuperação."
      >
        <div className="space-y-3">
          <Lifestyle lifestyle={lifestyle} />
          <div className="rounded-xl border border-white/10 bg-card p-3">
            <StressChart stress={stress} />
          </div>
        </div>
      </PanelSection>
    </div>
  );
}
