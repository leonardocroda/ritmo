"use client";

// Painel Home — a resposta diária (design home-panel): fetch único em
// /api/home/today e a máquina de estados do HealthPanel — loading com
// skeletons (DSN-23, nunca spinner), error com a mensagem do contrato
// existente, empty orientando o primeiro sync com link para /perfil
// (CLR-11; sem botão de sync aqui — AD-023: ele mora no Perfil) e ready
// com a composição do mock: veredito → chips de roteamento → cards de
// recomendação. O veredito null SEM estado vazio (carga/treino sem
// sinal de saúde) não mostra frase — só o que existe.

import { useEffect, useState } from "react";
import Link from "next/link";

import { getHomeToday, type HomeToday } from "@/lib/api";
import PredictionsDigest from "@/components/home/PredictionsDigest";
import RecommendationCards from "@/components/home/RecommendationCards";
import RoutingChips from "@/components/home/RoutingChips";
import VerdictCard from "@/components/home/VerdictCard";
import VolumeMini from "@/components/home/VolumeMini";
import Skeleton from "@/components/Skeleton";

type PanelState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "empty" }
  | { kind: "ready"; data: HomeToday };

export default function HomePanel() {
  const [state, setState] = useState<PanelState>({ kind: "loading" });

  useEffect(() => {
    getHomeToday()
      .then((data) => {
        // Estado vazio = nenhum dado de saúde/carga/atividade (design
        // §Components): sem veredito, strip zerada e sem treino não há o
        // que dizer — orienta o primeiro sync em vez de frutrar.
        setState(
          data.verdict === null &&
            data.last_activity === null &&
            data.strip.every((point) => point.load === 0)
            ? { kind: "empty" }
            : { kind: "ready", data },
        );
      })
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : "Erro inesperado";
        setState({ kind: "error", message });
      });
  }, []);

  if (state.kind === "loading") {
    // Skeleton no lugar do texto de carregamento (DSN-23): o herói e a
    // linha de chips com a cara da composição que chega.
    return (
      <div className="mt-6 space-y-3">
        <Skeleton className="h-52 w-full rounded-card" />
        <div className="grid grid-cols-3 gap-2">
          <Skeleton className="h-14 rounded-ctl" />
          <Skeleton className="h-14 rounded-ctl" />
          <Skeleton className="h-14 rounded-ctl" />
        </div>
      </div>
    );
  }

  if (state.kind === "error") {
    return (
      <p className="mt-6 rounded-card border border-border bg-card px-4 py-3 text-sm text-muted">
        Não foi possível carregar a Home: {state.message}
      </p>
    );
  }

  if (state.kind === "empty") {
    return (
      <div className="mt-6 rounded-card border border-border bg-card px-4 py-6 text-sm text-muted">
        <p>
          Nada por aqui ainda. O primeiro sync puxa seus dados do Garmin — o
          botão mora no Perfil.
        </p>
        <Link
          href="/perfil"
          className="mt-3 inline-flex min-h-11 items-center rounded-full border border-border px-4 py-2 font-medium text-foreground transition-colors hover:border-border-hover"
        >
          Ir para o Perfil →
        </Link>
      </div>
    );
  }

  const { data } = state;

  return (
    <div className="mt-4 space-y-3">
      {data.verdict !== null && (
        <VerdictCard
          verdict={data.verdict}
          signals={data.signals}
          strip={data.strip}
          date={data.date}
        />
      )}
      <RoutingChips
        lastActivity={data.last_activity}
        volume={data.volume}
        countdown={data.countdown}
        date={data.date}
      />
      {data.recommendations.length > 0 && (
        <RecommendationCards recommendations={data.recommendations} />
      )}
      {/* Digests P2 abaixo da dobra — bloco omitido quando não há o que
          dizer (volume_weeks null sem corridas; predictions null com a
          calibração indisponível) */}
      {data.volume_weeks !== null && data.volume !== null && (
        <VolumeMini
          volume={data.volume}
          weeks={data.volume_weeks}
          acwr={data.signals.fitness?.acwr ?? null}
        />
      )}
      {data.predictions !== null && (
        <PredictionsDigest predictions={data.predictions} />
      )}
    </div>
  );
}
