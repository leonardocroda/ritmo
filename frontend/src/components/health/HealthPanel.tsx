"use client";

// Painel Saúde (§4.5) — página-composição: busca /api/health/summary em 1
// round-trip e monta as 5 seções do fio condutor (panel-clarity): Sono →
// Carga de treino → Recuperação → Dose-resposta → Equilíbrio de vida,
// cada uma com cabeçalho forte numerado (PanelSection — CLR-12/13) e a
// linha-guia conectando tudo no topo (CLR-26). Bloco null -> estado
// vazio próprio do bloco (HLT-19); painel inteiro vazio (sono, HRV,
// RHR, estresse e PMC ausentes) -> estado vazio apontando o sync
// (CLR-11) — só com `load`, a seção Carga já renderiza com dados.

import { useEffect, useState, type ReactNode } from "react";

import { getHealthSummary, type HealthSummaryOut } from "@/lib/api";
import PanelSection from "@/components/PanelSection";
import DoseResponse from "@/components/health/DoseResponse";
import HrvChart from "@/components/health/HrvChart";
import Lifestyle from "@/components/health/Lifestyle";
import PmcChart from "@/components/health/PmcChart";
import RemChart from "@/components/health/RemChart";
import RhrChart from "@/components/health/RhrChart";
import SleepChart from "@/components/health/SleepChart";
import SleepStagesChart from "@/components/health/SleepStagesChart";
import StressChart from "@/components/health/StressChart";
import WeekdayPattern from "@/components/health/WeekdayPattern";

type PanelState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; panel: HealthSummaryOut };

/** Estado vazio de um bloco — orienta o primeiro sync, sem erro (HLT-19). */
function BlockEmpty({ children }: { children: ReactNode }) {
  return (
    <p className="rounded-xl border border-white/10 bg-card px-4 py-6 text-sm text-muted">
      {children}
    </p>
  );
}

export default function HealthPanel() {
  const [state, setState] = useState<PanelState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    getHealthSummary()
      .then((panel) => {
        if (!cancelled) setState({ kind: "ready", panel });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setState({
          kind: "error",
          message: err instanceof Error ? err.message : "Erro inesperado",
        });
      });
    return () => {
      cancelled = true;
    };
  }, []);

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

  const { sleep, hrv, rhr, stress, pmc, dose_response, lifestyle } = state.panel;

  // Estado vazio geral (CLR-11): painel vazio somente com sono, HRV, RHR,
  // estresse E PMC ausentes — com `load` no banco a seção Carga de treino
  // renderiza com dados (padrão WorkoutsList, HLT-28 evoluído).
  if (
    sleep === null &&
    hrv === null &&
    rhr === null &&
    stress === null &&
    pmc === null
  ) {
    return (
      <p className="mt-6 rounded-xl border border-white/10 bg-card px-4 py-6 text-sm text-muted">
        Nada por aqui ainda. Use o botão &ldquo;Puxar do Garmin&rdquo; no topo
        para sincronizar seus dados.
      </p>
    );
  }

  return (
    <div className="mt-4">
      {/* Linha-guia (CLR-26): o fio que conecta as 5 seções */}
      <p className="text-sm text-muted">
        O fio: o sono recupera, o treino impõe carga, o corpo responde,
        dormir mal custa — e a vida fora da corrida sustenta tudo.
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
        title="Carga de treino"
        subtitle="Quanta carga estou impondo ao corpo? A curva de 60 dias traz fitness (CTL), fadiga (ATL) e forma (TSB) — carga acima da que o corpo absorve compromete recuperação e adaptação."
      >
        {pmc !== null ? (
          <div className="rounded-xl border border-white/10 bg-card p-3">
            <PmcChart pmc={pmc} />
          </div>
        ) : (
          <BlockEmpty>
            Sem curva de carga ainda — ela nasce no primeiro sync, que acumula
            o treino dos últimos dias.
          </BlockEmpty>
        )}
      </PanelSection>

      <PanelSection
        index={3}
        title="Recuperação"
        subtitle="Como o corpo está respondendo? HRV noturna e frequência cardíaca de repouso — os sinais diários de quanto da carga está virando adaptação."
      >
        <div className="space-y-3">
          {hrv !== null ? (
            <div className="rounded-xl border border-white/10 bg-card p-3">
              <HrvChart hrv={hrv} />
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
        index={4}
        title="Dose-resposta"
        subtitle="O que dormir mal me custa? Noites curtas (<6h) contra noites adequadas (≥6h45) — HRV e score médios da mesma noite mostram o preço."
      >
        <DoseResponse dose={dose_response} />
      </PanelSection>

      <PanelSection
        index={5}
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
