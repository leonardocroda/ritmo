"use client";

// Painel Saúde (§4.5) — página-composição: busca /api/health/summary em 1
// round-trip e monta as seções condicionalmente (padrão PotentialPanel):
// Sono (duração vs piso, fases, REM, regularidade + padrão semanal),
// Recuperação (HRV + RHR), Dose-resposta e Equilíbrio de vida (força,
// yoga, estresse). Bloco null -> estado vazio próprio do bloco (HLT-19);
// painel inteiro vazio -> estado vazio apontando o sync (HLT-28).

import { useEffect, useState, type ReactNode } from "react";

import { getHealthSummary, type HealthSummaryOut } from "@/lib/api";
import DoseResponse from "@/components/health/DoseResponse";
import HrvChart from "@/components/health/HrvChart";
import Lifestyle from "@/components/health/Lifestyle";
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

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mt-6">
      <h2 className="text-sm font-medium text-muted">{title}</h2>
      <div className="mt-2">{children}</div>
    </section>
  );
}

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

  const { sleep, hrv, rhr, stress, dose_response, lifestyle } = state.panel;

  // Estado vazio geral (padrão WorkoutsList): nenhuma série de saúde no
  // banco — aponta o sync (HLT-28).
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
      <Section title="Sono">
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
      </Section>

      <Section title="Recuperação">
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
      </Section>

      <Section title="Dose-resposta">
        <DoseResponse dose={dose_response} />
      </Section>

      <Section title="Equilíbrio de vida">
        <div className="space-y-3">
          <Lifestyle lifestyle={lifestyle} />
          <div className="rounded-xl border border-white/10 bg-card p-3">
            <StressChart stress={stress} />
          </div>
        </div>
      </Section>
    </div>
  );
}
