"use client";

// /perfil — nasce aqui com a tela de zonas de FC (feature hr-zones):
// seção 1 "Valores" (HRZ-13/14); as seções 2 (Método e zonas) e 3
// (Histórico) chegam na T12. Página client no padrão do /login: o
// proxy protege a rota (sem cookie → /login?next=/perfil, HRZ-16) e o
// apiFetch redireciona na sessão expirada em uso. O GET carrega o
// shape completo; cada seção que salva chama o PUT e a página
// re-renderiza da resposta — "salvar → zonas mudam na hora".

import { useEffect, useState } from "react";

import PanelSection from "@/components/PanelSection";
import HrValuesCard from "@/components/profile/HrValuesCard";
import { getHrZones, type HrZonesOut } from "@/lib/api";

type PageState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; data: HrZonesOut };

export default function PerfilPage() {
  const [state, setState] = useState<PageState>({ kind: "loading" });

  useEffect(() => {
    getHrZones()
      .then((data) => setState({ kind: "ready", data }))
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : "Erro inesperado";
        setState({ kind: "error", message });
      });
  }, []);

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-6 sm:px-6">
      <h1 className="text-2xl font-semibold tracking-tight">Perfil</h1>
      {state.kind === "loading" && (
        <p className="mt-6 text-sm text-muted">Carregando perfil…</p>
      )}
      {state.kind === "error" && (
        <p className="mt-6 rounded-xl border border-white/10 bg-card px-4 py-3 text-sm text-muted">
          Não foi possível carregar o perfil: {state.message}
        </p>
      )}
      {state.kind === "ready" && (
        <>
          <PanelSection
            index={1}
            title="Valores"
            subtitle="Quais são os seus números? FC máxima, FC de repouso e LTHR — a matéria-prima das zonas. O sync do Garmin preenche os três (a FC de repouso vem do mínimo dos últimos 7 dias); a edição manual aqui vence e nunca é sobrescrita."
          >
            <HrValuesCard
              metrics={state.data.metrics}
              onSaved={(out) => setState({ kind: "ready", data: out })}
            />
          </PanelSection>
          {/* Seção 2 "Método e zonas" — T12 (feature hr-zones) */}
          {/* Seção 3 "Histórico" — T12 (feature hr-zones) */}
        </>
      )}
    </main>
  );
}
