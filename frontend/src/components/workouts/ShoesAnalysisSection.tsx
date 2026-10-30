"use client";

import { useEffect, useState } from "react";
import { formatKm, formatPace, formatDuration } from "@/lib/format";
import PanelSection from "@/components/PanelSection";
import Skeleton from "@/components/Skeleton";
import {
  getAnalysisShoes,
  getAnalysisCompare,
  getDegradation,
  getShoes,
  type AnalysisShoeProfile,
  type AnalysisCompare,
  type DegradationOut,
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
  const [compareA, setCompareA] = useState<number | null>(null);
  const [compareB, setCompareB] = useState<number | null>(null);
  const [compareRes, setCompareRes] = useState<AnalysisCompare | null>(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [degradation, setDegradation] = useState<DegradationOut | null>(null);
  const [degradationLoading, setDegradationLoading] = useState(false);

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

  useEffect(() => {
    if (!selectedId) return;
    let cancelled = false;
    setDegradationLoading(true);
    getDegradation(selectedId)
      .then(d => { if (!cancelled) setDegradation(d); })
      .catch(() => { if (!cancelled) setDegradation(null); })
      .finally(() => { if (!cancelled) setDegradationLoading(false); });
    return () => { cancelled = true; };
  }, [selectedId]);

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

  async function runCompare() {
    if (!compareA || !compareB || compareA === compareB) return;
    setCompareLoading(true);
    try {
      const res = await getAnalysisCompare(compareA, compareB);
      setCompareRes(res);
    } catch {
      setCompareRes(null);
    } finally {
      setCompareLoading(false);
    }
  }

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
        <div className="md:col-span-2 space-y-4">
          <div className="rounded-card border border-border bg-card p-4">
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

          <div className="rounded-card border border-border bg-card p-4">
            <h3 className="font-semibold mb-2">Comparação pareada</h3>
            <div className="flex gap-2 items-end">
              <select className="rounded border border-border bg-card px-3 py-2 text-sm" value={compareA ?? ""} onChange={e => setCompareA(Number(e.target.value) || null)}>
                <option value="">Tênis A</option>
                {shoes.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
              <select className="rounded border border-border bg-card px-3 py-2 text-sm" value={compareB ?? ""} onChange={e => setCompareB(Number(e.target.value) || null)}>
                <option value="">Tênis B</option>
                {shoes.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
              <button onClick={runCompare} disabled={!compareA || !compareB || compareLoading} className="rounded px-3 py-2 text-sm bg-accent/15 text-accent">
                {compareLoading ? "Comparando..." : "Comparar"}
              </button>
            </div>
            {compareRes && (
              <div className="mt-3 text-sm">
                <p className="text-muted">Pares: {compareRes.n_pairs} · Confiança: {compareRes.confidence}</p>
                <div className="mt-2 max-h-60 overflow-auto space-y-1">
                  {compareRes.pairs.map((p, i) => (
                    <div key={i} className="rounded border border-border p-2 text-xs">
                      {formatKm(p.distance_m)} · A {formatPace(p.pace_a_s)}/km / B {formatPace(p.pace_b_s)}/km · Δ {p.delta_pace_s}s · FC Δ {p.delta_fc ?? "-"}
                    </div>
                  ))}
                  {compareRes.pairs.length === 0 && <p className="text-muted">Sem pares válidos.</p>}
                </div>
              </div>
            )}
          </div>

          <div className="rounded-card border border-border bg-card p-4">
            <h3 className="font-semibold mb-2">Alerta de degradação</h3>
            {degradationLoading ? (
              <Skeleton className="h-10 w-full rounded" />
            ) : degradation ? (
              degradation.insufficient ? (
                <p className="text-sm text-muted">Dados insuficientes (mínimo ~150 km).</p>
              ) : (
                <div className="text-sm space-y-2">
                  <p className="text-muted">Total {formatKm(degradation.total_km * 1000)} · {degradation.n_runs ?? 0} corridas · sinais: {degradation.n_signals}</p>
                  {degradation.signals.length > 0 ? (
                    <div className="space-y-1">
                      {degradation.signals.map((s, i) => (
                        <div key={i} className="rounded border border-border p-2 text-xs">
                          <span className="font-medium">{s.label}</span> — inicial {s.inicial} {s.unidade} / final {s.final} {s.unidade} · Δ {s.delta} · {s.direcao ?? "-"}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-muted">Sem sinais detectados.</p>
                  )}
                </div>
              )
            ) : (
              <p className="text-sm text-muted">Sem dados de degradação.</p>
            )}
          </div>
        </div>
      </div>
    </PanelSection>
  );
}
