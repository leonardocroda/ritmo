"use client";

// Painel Potencial (§4.4) — página-composição: busca /api/potential em 1
// round-trip e monta as seções condicionalmente (padrão WorkoutDetail):
// card da lacuna com a narrativa honesta de §9.5 + timeline VDOT com
// faixa (AD-004), previsões vs PRs, curva PMC, VO2max do relógio (só
// quando existe — POT-27) e decaimento (só com PRs canônicos).

import { useEffect, useState, type ReactNode } from "react";

import { getPotential, type PotentialOut, type VdotBlock } from "@/lib/api";
import { formatVdot } from "@/lib/format";
import DecayTable from "@/components/potential/DecayTable";
import PmcChart from "@/components/potential/PmcChart";
import PredictionsTable from "@/components/potential/PredictionsTable";
import VdotTimeline from "@/components/potential/VdotTimeline";
import Vo2maxTrend from "@/components/potential/Vo2maxTrend";

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
    <div className="rounded-xl border border-white/10 bg-card px-4 py-3">
      <p className="flex items-baseline gap-2">
        <span className="text-3xl font-semibold tracking-tight tabular-nums">
          {gap_pct !== null ? `${formatVdot(gap_pct)}%` : "—"}
        </span>
        <span className="text-sm text-muted">do potencial já liberado</span>
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

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mt-6">
      <h2 className="text-sm font-medium text-muted">{title}</h2>
      <div className="mt-2">{children}</div>
    </section>
  );
}

export default function PotentialPanel() {
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
    return <p className="mt-6 text-sm text-muted">Carregando potencial…</p>;
  }

  if (state.kind === "error") {
    return (
      <p className="mt-6 rounded-xl border border-white/10 bg-card px-4 py-3 text-sm text-muted">
        Não foi possível carregar o potencial: {state.message}
      </p>
    );
  }

  const { vdot, predictions, pmc, vo2max, decay } = state.panel;

  // Estado vazio (padrão WorkoutsList): nada de pessoal no banco — só o
  // teste de calibração do arquivo, sem PMC/VO2max/PRs — aponta o sync.
  if (
    vdot.timeline.length <= 1 &&
    pmc === null &&
    vo2max === null &&
    decay.length === 0
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
      <GapCard vdot={vdot} />

      <Section title="Timeline VDOT">
        <div className="rounded-xl border border-white/10 bg-card p-3">
          <VdotTimeline vdot={vdot} />
        </div>
      </Section>

      <Section title="Previsões vs PRs">
        <PredictionsTable predictions={predictions} />
      </Section>

      {pmc !== null ? (
        <Section title="Carga (PMC)">
          <div className="rounded-xl border border-white/10 bg-card p-3">
            <PmcChart pmc={pmc} />
          </div>
        </Section>
      ) : (
        <Section title="Carga (PMC)">
          <p className="rounded-xl border border-white/10 bg-card px-4 py-6 text-sm text-muted">
            Sem curva de carga ainda — ela nasce no primeiro sync, que acumula
            o treino dos últimos dias.
          </p>
        </Section>
      )}

      {vo2max !== null && (
        <Section title="VO2max">
          <div className="rounded-xl border border-white/10 bg-card p-3">
            <Vo2maxTrend vo2max={vo2max} />
          </div>
        </Section>
      )}

      {decay.length > 0 && (
        <Section title="Decaimento por distância">
          <DecayTable rows={decay} />
        </Section>
      )}
    </div>
  );
}
