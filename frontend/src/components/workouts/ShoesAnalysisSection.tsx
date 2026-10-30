"use client";

import { useEffect, useState } from "react";
import { formatKm, formatPace, formatDuration } from "@/lib/format";
import PanelSection from "@/components/PanelSection";
import Skeleton from "@/components/Skeleton";
import {
  getAnalysisShoes,
  getShoes,
  type AnalysisShoeProfile,
  type Shoe,
  type ShoesOut,
} from "@/lib/api";

type PanelState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "empty" }
  | { kind: "ready"; shoes: Shoe[]; profiles: Map<number, AnalysisShoeProfile> };

function groupLabel(tipo: string, banda: string) {
  return `${tipo} · ${banda}`;
}

export default function ShoesAnalysisSection() {
  const [state, setState] = useState<PanelState>({ kind: "loading" });
  const [selectedId, setSelectedId] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [shoesOut, profiles] = await Promise.all([
          getShoes(),
          getAnalysisShoes(),
        ]);
        if (cancelled) return;
        const map = new Map<number, AnalysisShoeProfile>();
        for (const p of profiles) map.set(p.shoe_id, p);
        if (shoesOut.items.length === 0) {
          setState({ kind: "empty" });
        } else {
          setState({ kind: "ready", shoes: shoesOut.items, profiles: map });
        }
      } catch (err: unknown) {
        if (!cancelled) {
          setState({ kind: "error", message: err instanceof Error ? err.message : "Erro ao carregar análise" });
        }
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  if (state.kind === "loading") {
    return (
      <PanelSection title="Análise de tênis">
        <div className="space-y-2">
          <Skeleton className="h-24 w-full rounded-card" />
          <Skeleton className="h-24 w-full rounded-card" />
        </div>
      </PanelSection>
    );
  }

  if (state.kind === "error") {
    return (
      <PanelSection title="Análise de tênis">
        <p className="rounded-card border border-border bg-card px-4 py-3 text-sm text-muted">{state.message}</p>
      </PanelSection>
    );
  }

  if (state.kind === "empty") {
    return (
      <PanelSection title="Análise de tênis">
        <p className="rounded-card border border-border bg-card px-4 py-6 text-sm text-muted">
          Nenhum tênis cadastrado ainda.
        </p>
      </PanelSection>
    );
  }

  const { shoes, profiles } = state;
  const selectedShoe = shoes.find(s => s.id === selectedId) ?? shoes[0];
  const profile = selectedShoe ? profiles.get(selectedShoe.id) : undefined;

  return (
    <PanelSection title="Análise de tênis">
      <div className="grid gap-4 md:grid-cols-3">
        <div className="md:col-span-1 space-y-2">
          {shoes.map(s => (
            <button
              key={s.id}
              onClick={() => setSelectedId(s.id)}
              className={`w-full rounded-card border px-4 py-3 text-left hover:border-accent/40 ${
                selectedId === s.id ? "border-accent bg-accent/5" : "border-border bg-card"
              }`}
            >
              <p className="font-medium">{s.name}</p>
              <p className="text-xs text-muted">{s.status} · {s.current_km.toFixed(1)} km</p>
            </button>
          ))}
        </div>
        <div className="md:col-span-2 rounded-card border border-border bg-card p-4">
          {profile ? (
            <div>
              <h3 className="font-semibold">Perfil — {selectedShoe.name}</h3>
              <p className="text-sm text-muted">{profile.total_runs} corridas · {formatKm(profile.total_km * 1000)}</p>
              <div className="mt-3 space-y-2">
                {profile.groups.map((g, i) => (
                  <div key={i} className="rounded border border-border p-3 text-sm">
                    <div className="font-medium">{groupLabel(g.tipo, g.banda)}</div>
                    <div className="text-muted">
                      {g.n_corridas} corridas · {formatKm(g.km_totais * 1000)} · 
                      {g.pace_medio_s ? ` ${formatPace(g.pace_medio_s)}/km` : ` ${formatDuration(0)}`} ·
                      {g.fc_media ? ` ${g.fc_media.toFixed(0)} bpm` : ""}
                    </div>
                  </div>
                ))}
                {profile.groups.length === 0 && (
                  <p className="text-sm text-muted">Sem dados suficientes para perfil.</p>
                )}
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted">Sem dados de análise para este tênis.</p>
          )}
        </div>
      </div>
    </PanelSection>
  );
}
