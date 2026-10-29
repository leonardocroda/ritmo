"use client";

import { useEffect, useState } from "react";

import PanelSection from "@/components/PanelSection";
import Skeleton from "@/components/Skeleton";
import RecalibrateModal from "@/components/profile/RecalibrateModal";
import { getPaceZones, type PaceZonesOut } from "@/lib/api";

type PageState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; data: PaceZonesOut };

export default function PaceZonesPage() {
  const [state, setState] = useState<PageState>({ kind: "loading" });
  const [showRecalibrate, setShowRecalibrate] = useState(false);

  useEffect(() => {
    getPaceZones()
      .then((data) => setState({ kind: "ready", data }))
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : "Erro inesperado";
        setState({ kind: "error", message });
      });
  }, []);

  function formatPaceRange(zone: PaceZonesOut["zones"]["easy"]): string {
    if (zone.pace_range) {
      return zone.pace_range.replace("-", "–");
    }
    return zone.pace || "—";
  }

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-6 sm:px-6">
      <h1 className="text-2xl font-semibold tracking-tight">Zonas de Ritmo</h1>

      {state.kind === "loading" && (
        <div className="mt-6 space-y-4">
          <Skeleton className="h-5 w-1/3 rounded-ctl" />
          <Skeleton className="h-32 w-full rounded-card" />
          <Skeleton className="h-4 w-2/3 rounded-ctl" />
          <Skeleton className="h-4 w-1/2 rounded-ctl" />
        </div>
      )}

      {state.kind === "error" && (
        <p className="mt-6 rounded-card border border-border bg-card px-4 py-3 text-sm text-muted">
          Não foi possível carregar as zonas de ritmo: {state.message}
        </p>
      )}

      {state.kind === "ready" && (
        <>
          <PanelSection
            index={1}
            title="VDOT e Teste"
            subtitle="Seu VDOT atual, a fonte do cálculo e a data do teste de referência."
          >
            <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3 text-sm">
              <div>
                <dt className="text-muted">VDOT</dt>
                <dd className="font-mono text-lg font-semibold">{state.data.vdot}</dd>
              </div>
              <div>
                <dt className="text-muted">Fonte</dt>
                <dd className="font-medium">{state.data.source}</dd>
              </div>
              <div>
                <dt className="text-muted">Data do teste</dt>
                <dd className="font-medium">{state.data.test_date}</dd>
              </div>
              <div>
                <dt className="text-muted">Distância</dt>
                <dd className="font-mono font-medium">
                  {(state.data.distancia_metros / 1000).toFixed(3)} km
                </dd>
              </div>
              <div>
                <dt className="text-muted">Tempo</dt>
                <dd className="font-mono font-medium">
                  {Math.floor(state.data.tempo_segundos / 60)}:{String(state.data.tempo_segundos % 60).padStart(2, "0")}
                </dd>
              </div>
            </dl>
          </PanelSection>

          <PanelSection
            index={2}
            title="Zonas de Ritmo"
            subtitle="As 5 zonas de Jack Daniels: pace, descrição e cor (legenda do gráfico de voltas)."
          >
            <div className="space-y-3">
              {([
                { key: "easy", label: "Easy (Recuperação)" },
                { key: "marathon", label: "Maratona" },
                { key: "threshold", label: "Limiar" },
                { key: "interval", label: "Intervalado" },
                { key: "repetition", label: "Repetição" },
              ] as const).map(({ key, label }) => {
                const zone = state.data.zones[key];
                const color = (() => {
                  switch (key) {
                    case "easy": return "bg-green-500";
                    case "marathon": return "bg-blue-500";
                    case "threshold": return "bg-orange-500";
                    case "interval": return "bg-red-500";
                    case "repetition": return "bg-purple-500";
                  }
                })();

                return (
                  <div
                    key={key}
                    className="flex items-center gap-3 rounded-card border border-border bg-card px-4 py-3"
                  >
                    <span className={`flex size-3 rounded-full ${color}`} aria-hidden="true" />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{label}</p>
                      <p className="text-sm text-muted font-mono">{formatPaceRange(zone)}</p>
                    </div>
                    <p className="text-sm text-muted whitespace-nowrap">{zone.description}</p>
                  </div>
                );
              })}
            </div>
          </PanelSection>

          <PanelSection
            index={3}
            title="Equivalências de Prova"
            subtitle="Tempos estimados para distâncias canônicas baseados no seu VDOT atual."
          >
            <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4 text-sm">
              {(["5K", "10K", "Meia Maratona", "Maratona"] as const).map((race) => (
                <div key={race}>
                  <dt className="text-muted">{race}</dt>
                  <dd className="font-mono font-medium">{state.data.equivalencias[race]}</dd>
                </div>
              ))}
            </dl>
          </PanelSection>

          <PanelSection
            index={4}
            title="Recalibração"
            subtitle="Atualize seu VDOT quando fizer um novo teste máximo."
          >
            <button
              type="button"
              onClick={() => setShowRecalibrate(true)}
              className="flex w-full items-center gap-3 rounded-card border border-border bg-card px-4 py-3 hover:border-accent/40 text-left"
            >
              <div className="flex items-center gap-3">
                <span className="flex size-9 items-center justify-center rounded-full bg-accent/15 text-accent">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M12 20.3C7.4 16.7 3.5 13.4 3.5 9.6 3.5 6.9 5.4 5 7.9 5c1.6 0 3.1.8 4.1 2.2C13 5.8 14.5 5 16.1 5c2.5 0 4.4 1.9 4.4 4.6 0 3.8-3.9 7.1-8.5 10.7Z" />
                    <path d="M12 8v8" />
                    <path d="M8 12h8" />
                  </svg>
                </span>
                <div>
                  <p className="font-medium">Recalibrar VDOT</p>
                  <p className="text-sm text-muted">Executar entrevista interativa no terminal do servidor</p>
                </div>
              </div>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="text-muted shrink-0">
                <path d="M9 18l6-6-6-6" />
              </svg>
            </button>
          </PanelSection>
        </>
      )}

      <RecalibrateModal isOpen={showRecalibrate} onClose={() => setShowRecalibrate(false)} />
    </main>
  );
}