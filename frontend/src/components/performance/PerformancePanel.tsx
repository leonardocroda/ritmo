"use client";

// Painel Performance (ex-Potencial, §4.4 — AD-017) — página-composição:
// busca /api/potential em 1
// round-trip e monta os 4 blocos narrativos (CLR-17 + AD-017): Onde
// estou → O que isso prevê → O que o relógio estima → Carga de treino
// (a curva PMC voltou pra cá, janela fixa de 60d). Card da lacuna
// com a narrativa honesta de §9.5 + timeline VDOT com faixa (AD-004),
// previsões vs PRs, decaimento (só com PRs canônicos) e VO2max do relógio
// (bloco inteiro ausente quando não existe — POT-27/CLR-22). A
// linha-guia do topo carrega a pergunta do painel e a régua
// provas/testes > estimativas (AD-005, CLR-27).

import { useEffect, useState } from "react";

import { getPotential, type PotentialOut, type VdotBlock } from "@/lib/api";
import { formatVdot } from "@/lib/format";
import PanelSection from "@/components/PanelSection";
import Skeleton from "@/components/Skeleton";
import DecayTable from "@/components/performance/DecayTable";
import PmcChart from "@/components/performance/PmcChart";
import PredictionsTable from "@/components/performance/PredictionsTable";
import VdotTimeline from "@/components/performance/VdotTimeline";
import Vo2maxTrend from "@/components/performance/Vo2maxTrend";

type PanelState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; panel: PotentialOut };

/** "2026-04-26" -> "26/04/2026" (wall clock, sem conversão de fuso). */
function formatDay(date: string): string {
  const [year, month, day] = date.split("-");
  return `${day}/${month}/${year}`;
}

/** Card da lacuna (POT-18): gap_pct + narrativa honesta de §9.5. */
function GapCard({ vdot }: { vdot: VdotBlock }) {
  const { current, demonstrated, gap_pct } = vdot;
  return (
    <div className="rounded-card border border-border bg-card px-4 py-3">
      <p className="flex items-baseline gap-2">
        <span className="text-3xl font-semibold tracking-tight tabular-nums">
          {gap_pct !== null ? `${formatVdot(gap_pct)}%` : "—"}
        </span>
        <span className="text-sm text-muted">
          do potencial demonstrado que o teste atual valida
        </span>
      </p>
      {demonstrated !== null && (
        <p className="mt-2 text-sm">
          Você já demonstrou {formatVdot(demonstrated.vdot)} ({demonstrated.source},{" "}
          {formatDay(demonstrated.date)}); o teste atual valida{" "}
          {formatVdot(current.vdot)} — o meio é o alvo honesto.
        </p>
      )}
    </div>
  );
}

export default function PerformancePanel() {
  const [state, setState] = useState<PanelState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    getPotential()
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
    // Skeleton no lugar do texto de carregamento (DSN-23): linha-guia
    // + card da lacuna + cartão de gráfico.
    return (
      <div className="mt-6 space-y-3">
        <Skeleton className="h-4 w-2/3 rounded-ctl" />
        <Skeleton className="h-32 w-full rounded-card" />
        <Skeleton className="h-56 w-full rounded-card" />
      </div>
    );
  }

  if (state.kind === "error") {
    return (
      <p className="mt-6 rounded-card border border-border bg-card px-4 py-3 text-sm text-muted">
        Não foi possível carregar o potencial: {state.message}
      </p>
    );
  }

  const { vdot, predictions, vo2max, decay, pmc } = state.panel;

  // Estado vazio recalculado com o pmc de volta (CLR-24 evoluído —
  // AD-017): nada de pessoal no banco — só o teste de calibração do
  // arquivo, sem VO2max/PRs e sem linhas de carga — aponta o sync.
  if (
    vdot.timeline.length <= 1 &&
    vo2max === null &&
    decay.length === 0 &&
    pmc === null
  ) {
    return (
      <p className="mt-6 rounded-card border border-border bg-card px-4 py-6 text-sm text-muted">
        Nada por aqui ainda. Use o botão &ldquo;Puxar do Garmin&rdquo; no topo
        para sincronizar seus dados.
      </p>
    );
  }

  return (
    <div className="mt-4">
      {/* Linha-guia (CLR-27): a pergunta do painel + a régua de leitura */}
      <p className="text-sm text-muted">
        Qual é o meu máximo, a que distância dele estou — e quanta carga
        estou impondo pra chegar lá? A régua: provas e testes de campo
        medem, estimativas do relógio só aproximam.
      </p>

      <PanelSection
        title="Onde estou"
        subtitle="VDOT é a régua de equivalência de Daniels — um tempo numa distância vira capacidade aeróbica. O corrente vem do último teste calibrado, o demonstrado da melhor prova máxima; a lacuna % é quanto do demonstrado o teste atual valida."
      >
        <div className="space-y-3">
          <GapCard vdot={vdot} />
          <div className="rounded-card border border-border bg-card p-3">
            <VdotTimeline vdot={vdot} />
          </div>
        </div>
      </PanelSection>

      <PanelSection
        title="O que isso prevê"
        subtitle="O que cada método prevê para 5K, 10K, meia e maratona contra os seus PRs — e o decaimento por distância: onde o pace real foge do ideal da equivalência."
      >
        <div className="space-y-3">
          <PredictionsTable predictions={predictions} />
          {decay.length > 0 && <DecayTable rows={decay} />}
        </div>
      </PanelSection>

      {vo2max !== null && (
        <PanelSection
          title="O que o relógio estima"
          subtitle="Tendência do VO2max que o algoritmo do relógio estima a partir de ritmo e FC — referência que fica abaixo de provas e testes na hierarquia de métricas."
        >
          <div className="rounded-card border border-border bg-card p-3">
            <Vo2maxTrend vo2max={vo2max} />
          </div>
        </PanelSection>
      )}

      <PanelSection
        title="Carga de treino"
        subtitle="O motor por trás do número: quanta carga estou impondo ao corpo? A curva de 60 dias traz fitness (CTL), fadiga (ATL) e forma (TSB) — carga acima da que o corpo absorve compromete recuperação e adaptação."
      >
        {pmc !== null ? (
          <div className="rounded-card border border-border bg-card p-3">
            <PmcChart pmc={pmc} />
          </div>
        ) : (
          <p className="rounded-card border border-border bg-card px-4 py-6 text-sm text-muted">
            Sem curva de carga ainda — ela nasce no primeiro sync, que acumula
            o treino dos últimos dias.
          </p>
        )}
      </PanelSection>
    </div>
  );
}
