"use client";

// /zonas-fc — gestão de zonas de FC (Valores, Método e zonas, Histórico).
// Página client no padrão do /perfil: carrega estado completo (zonas + histórico + conexão)
// e lida com saves via handleSaved (re-renderiza na hora + rebusca histórico).

import { useEffect, useRef, useState } from "react";

import PanelSection from "@/components/PanelSection";
import Skeleton from "@/components/Skeleton";
import HrHistoryList from "@/components/profile/HrHistoryList";
import HrMethodCard from "@/components/profile/HrMethodCard";
import HrValuesCard from "@/components/profile/HrValuesCard";
import HrZonesPreview from "@/components/profile/HrZonesPreview";
import {
  getHrZones,
  getHrZonesHistory,
  type HrZonesHistory,
  type HrZonesOut,
} from "@/lib/api";

type PageState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | {
      kind: "ready";
      data: HrZonesOut;
      history: HrZonesHistory;
    };

export default function ZonasFcPage() {
  const [state, setState] = useState<PageState>({ kind: "loading" });
  const historySeq = useRef(0);

  useEffect(() => {
    Promise.all([getHrZones(), getHrZonesHistory()])
      .then(([data, history]) => setState({ kind: "ready", data, history }))
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : "Erro inesperado";
        setState({ kind: "error", message });
      });
  }, []);

  // Resposta do PUT vira o estado (zonas mudam na hora) e o
  // histórico é rebuscado — o PUT criou linha(s) nova(s).
  function handleSaved(out: HrZonesOut) {
    setState((prev) =>
      prev.kind === "ready" ? { ...prev, data: out } : prev,
    );
    const seq = ++historySeq.current;
    getHrZonesHistory()
      .then((history) => {
        if (seq !== historySeq.current) return;
        setState((prev) =>
          prev.kind === "ready" ? { ...prev, history } : prev,
        );
      })
      .catch(() => {});
  }

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-6 sm:px-6">
      <h1 className="text-2xl font-semibold tracking-tight">Zonas de FC</h1>
      {state.kind === "loading" && (
        <div className="mt-6 space-y-3">
          <Skeleton className="h-5 w-1/3 rounded-ctl" />
          <Skeleton className="h-56 w-full rounded-card" />
          <Skeleton className="h-4 w-2/3 rounded-ctl" />
          <Skeleton className="h-4 w-1/2 rounded-ctl" />
        </div>
      )}
      {state.kind === "error" && (
        <p className="mt-6 rounded-card border border-border bg-card px-4 py-3 text-sm text-muted">
          Não foi possível carregar as zonas: {state.message}
        </p>
      )}
      {state.kind === "ready" && (
        <>
          <PanelSection
            index={1}
            title="Valores"
            subtitle="Quais são os seus números? FC máxima, FC de repouso e LTHR — a matéria-prima das zonas. O sync do Garmin preenche os três (a FC de repouso vem do mínimo dos últimos 7 dias); a edição manual aqui vence até você mandar voltar a puxar do Garmin."
          >
            <HrValuesCard
              metrics={state.data.metrics}
              modes={state.data.modes}
              onSaved={handleSaved}
            />
          </PanelSection>
          <PanelSection
            index={2}
            title="Método e zonas"
            subtitle="Como as zonas são calculadas? Escolha o método — LTHR%, reserva cardíaca (Karvonen) ou FC máx% — e ajuste os percentuais por zona. Salvar recalcula as zonas em bpm na hora; treinos antigos continuam com as zonas da época deles."
          >
            <div className="space-y-3">
              <HrMethodCard
                config={state.data.config}
                defaults={state.data.defaults}
                onSaved={handleSaved}
              />
              <HrZonesPreview
                zones={state.data.zones}
                config={state.data.config}
                metrics={state.data.metrics}
              />
            </div>
          </PanelSection>
          <PanelSection
            index={3}
            title="Histórico"
            subtitle="O que mudou e quando? Cada mudança de valor ou de configuração vira uma entrada datada, mais recente primeiro — a edição manual vence o sync e nada é apagado: corrigir é salvar valor novo."
          >
            <HrHistoryList history={state.history} />
          </PanelSection>
        </>
      )}
    </main>
  );
}