"use client";

// /perfil — hub do usuário: Conexão Garmin + atalhos para Equipamentos e Zonas de FC.
// Página client no padrão do /login: o proxy protege a rota (sem
// cookie → /login?next=/perfil) e o apiFetch redireciona na
// sessão expirada em uso.

import { useEffect, useState } from "react";
import Link from "next/link";

import PanelSection from "@/components/PanelSection";
import ConnectionCard from "@/components/profile/ConnectionCard";
import Skeleton from "@/components/Skeleton";
import SyncButton from "@/components/SyncButton";
import {
  getGarminConnection,
  type GarminConnectionOut,
} from "@/lib/api";

type PageState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; connection: GarminConnectionOut };

export default function PerfilPage() {
  const [state, setState] = useState<PageState>({ kind: "loading" });

  useEffect(() => {
    getGarminConnection()
      .then((connection) => setState({ kind: "ready", connection }))
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : "Erro inesperado";
        setState({ kind: "error", message });
      });
  }, []);

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-6 sm:px-6">
      <h1 className="text-2xl font-semibold tracking-tight">Perfil</h1>
      {state.kind === "loading" && (
        <div className="mt-6 space-y-3">
          <Skeleton className="h-5 w-1/3 rounded-ctl" />
          <Skeleton className="h-32 w-full rounded-card" />
        </div>
      )}
      {state.kind === "error" && (
        <p className="mt-6 rounded-card border border-border bg-card px-4 py-3 text-sm text-muted">
          Não foi possível carregar o perfil: {state.message}
        </p>
      )}
      {state.kind === "ready" && (
        <>
          <PanelSection
            title="Conexão Garmin"
            subtitle="Como seus dados chegam aqui? O sync lê direto da sua conta Garmin usando os tokens salvos criptografados no banco — é ela que alimenta os painéis e as zonas. Reautenticação necessária significa que o último sync não conseguiu entrar na conta: o re-login é feito por CLI com o operador."
          >
            <ConnectionCard
              state={state.connection.state}
              tokensUpdatedAt={state.connection.tokens_updated_at}
            />
            <div className="mt-4">
              <SyncButton />
            </div>
          </PanelSection>
          <PanelSection
            index={1}
            title="Zonas de FC"
            subtitle="Valores (FC máx, repouso, LTHR), método de cálculo e histórico de mudanças."
          >
            <Link
              href="/zonas-fc"
              className="flex items-center justify-between gap-3 rounded-card border border-border bg-card px-4 py-3 hover:border-accent/40"
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
                  <p className="font-medium">Zonas de FC</p>
                  <p className="text-sm text-muted">Valores, método, zonas e histórico</p>
                </div>
              </div>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="text-muted shrink-0">
                <path d="M9 18l6-6-6-6" />
              </svg>
            </Link>
          </PanelSection>
          <PanelSection
            index={2}
            title="Equipamentos"
            subtitle="Seus tênis: quilometragem, vida útil e aposentadoria. Acesse para cadastrar, editar ou aposentar pares."
          >
            <Link
              href="/equipamentos"
              className="flex items-center justify-between gap-3 rounded-card border border-border bg-card px-4 py-3 hover:border-accent/40"
            >
              <div className="flex items-center gap-3">
                <span className="flex size-9 items-center justify-center rounded-full bg-accent/15 text-accent">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M6 16c0 1.1.9 2 2 2h8a2 2 0 0 0 2-2v-8a2 2 0 0 0-2-2h-8a2 2 0 0 0-2 2v8Z" />
                    <path d="M10 10h4" />
                    <path d="M12 8v4" />
                  </svg>
                </span>
                <div>
                  <p className="font-medium">Meus tênis</p>
                  <p className="text-sm text-muted">Gerenciar quilometragem e vida útil</p>
                </div>
              </div>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="text-muted shrink-0">
                <path d="M9 18l6-6-6-6" />
              </svg>
            </Link>
          </PanelSection>
          <PanelSection
            index={3}
            title="Zonas de Ritmo"
            subtitle="Seu VDOT e zonas de ritmo (Easy, Maratona, Limiar, Intervalado, Repetição) calculados pela calibração de Jack Daniels."
          >
            <Link
              href="/pace-zones"
              className="flex items-center justify-between gap-3 rounded-card border border-border bg-card px-4 py-3 hover:border-accent/40"
            >
              <div className="flex items-center gap-3">
                <span className="flex size-9 items-center justify-center rounded-full bg-accent/15 text-accent">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M12 2v4" />
                    <path d="M12 18v4" />
                    <path d="M4.93 4.93l2.83 2.83" />
                    <path d="M16.24 16.24l2.83 2.83" />
                    <path d="M2 12h4" />
                    <path d="M18 12h4" />
                    <path d="M4.93 19.07l2.83-2.83" />
                    <path d="M16.24 7.76l2.83-2.83" />
                  </svg>
                </span>
                <div>
                  <p className="font-medium">Zonas de Ritmo</p>
                  <p className="text-sm text-muted">VDOT, 5 zonas e equivalências de prova</p>
                </div>
              </div>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="text-muted shrink-0">
                <path d="M9 18l6-6-6-6" />
              </svg>
            </Link>
          </PanelSection>
        </>
      )}
    </main>
  );
}