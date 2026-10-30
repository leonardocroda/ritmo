"use client";

import { useEffect, useState } from "react";
import { formatKm, formatPace, formatDuration, formatInferredType } from "@/lib/format";
import PanelSection from "@/components/PanelSection";
import Skeleton from "@/components/Skeleton";
import {
  getAnalysisShoes,
  getAnalysisCompare,
  getDegradation,
  getShoes,
  type AnalysisShoeProfile,
  type AnalysisCompare,
  type AnalysisPair,
  type DegradationOut,
  type DegradationSignal,
  type Shoe,
  type ShoesOut,
} from "@/lib/api";

type PanelState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "empty" }
  | { kind: "ready"; shoes: Shoe[]; profiles: Map<number, AnalysisShoeProfile> };

type ViewMode = "perfil" | "comparacao" | "degradacao";

const CONFIDENCE_STYLE: Record<string, { bg: string; text: string; dot: string }> = {
  alto: { bg: "bg-lime/15", text: "text-lime", dot: "bg-lime" },
  medio: { bg: "bg-amber/15", text: "text-amber", dot: "bg-amber" },
  baixo: { bg: "bg-coral/15", text: "text-coral", dot: "bg-coral" },
};

const DIRECTION_STYLE: Record<string, { bg: string; text: string; label: string }> = {
  piorou: { bg: "bg-coral/15", text: "text-coral", label: "piorou" },
  melhorou: { bg: "bg-lime/15", text: "text-lime", label: "melhorou" },
  estável: { bg: "bg-border", text: "text-muted", label: "estável" },
};

function groupLabel(tipo: string, banda: string) {
  const t = formatInferredType(tipo as any);
  const b = banda === "sem_pace" ? "sem pace" : banda;
  return `${t} · ${b}`;
}

function ConfidenceBadge({ level }: { level: "baixo" | "medio" | "alto" }) {
  const s = CONFIDENCE_STYLE[level];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${s.bg} ${s.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
      {level}
    </span>
  );
}

function SignalRow({ signal }: { signal: DegradationSignal }) {
  const d = DIRECTION_STYLE[signal.direcao ?? "estável"];
  const deltaSign = signal.delta > 0 ? "+" : "";
  return (
    <div className="rounded-card border border-border bg-raised/50 p-3">
      <div className="flex items-center justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2 flex-wrap">
            <span className="font-medium truncate">{signal.label}</span>
            <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${d.bg} ${d.text}`}>
              {d.label}
            </span>
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-3 text-sm text-muted num">
            <span>inicial: <span className="text-text">{signal.inicial.toFixed(signal.unidade === "EF" ? 4 : 1)}</span> {signal.unidade}</span>
            <span>final: <span className="text-text">{signal.final.toFixed(signal.unidade === "EF" ? 4 : 1)}</span> {signal.unidade}</span>
            <span>Δ <span className={`font-medium ${signal.delta >= 0 && signal.sinal !== "ef" ? "text-coral" : signal.delta <= 0 && signal.sinal === "ef" ? "text-coral" : "text-lime"}`}>{deltaSign}{signal.delta.toFixed(signal.unidade === "EF" ? 4 : 1)}</span> {signal.unidade}</span>
            {signal.confianca && <span>confiança: {signal.confianca}</span>}
          </div>
        </div>
      </div>
    </div>
  );
}

function ProfileCard({ profile, shoeName }: { profile: AnalysisShoeProfile; shoeName: string }) {
  return (
    <div className="rounded-card border border-border bg-card p-4">
      <div className="mb-3 flex items-baseline justify-between gap-3 flex-wrap">
        <h3 className="font-semibold">Perfil — {shoeName}</h3>
        <div className="flex items-center gap-2 text-sm text-muted num">
          <span>{profile.total_runs} corridas</span>
          <span>·</span>
          <span>{formatKm(profile.total_km * 1000)}</span>
        </div>
      </div>

      {profile.groups.length === 0 ? (
        <p className="text-sm text-muted text-center py-4">Sem dados suficientes para perfil.</p>
      ) : (
        <div className="space-y-2">
          {profile.groups.map((g, i) => (
            <div key={i} className="rounded-lg border border-border bg-raised/30 p-3 hover:border-border-hover transition-colors">
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <span className="font-medium text-sm">{groupLabel(g.tipo, g.banda)}</span>
                <span className="text-xs text-muted whitespace-nowrap">
                  {g.n_corridas} corridas · {formatKm(g.km_totais * 1000)}
                </span>
              </div>
              <div className="mt-2 grid grid-cols-3 gap-2 text-sm">
                <div className="rounded-ctl bg-night/50 p-2 text-center">
                  <div className="text-muted text-xs">pace médio</div>
                  <div className="font-medium num text-text">
                    {g.pace_medio_s ? formatPace(g.pace_medio_s) + "/km" : "—"}
                  </div>
                </div>
                <div className="rounded-ctl bg-night/50 p-2 text-center">
                  <div className="text-muted text-xs">fc média</div>
                  <div className="font-medium num text-text">
                    {g.fc_media ? g.fc_media.toFixed(0) + " bpm" : "—"}
                  </div>
                </div>
                <div className="rounded-ctl bg-night/50 p-2 text-center">
                  <div className="text-muted text-xs">cadência</div>
                  <div className="font-medium num text-text">
                    {g.cadencia_media ? g.cadencia_media.toFixed(0) + " spm" : "—"}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ComparisonView({
  shoes,
  compareA,
  compareB,
  setCompareA,
  setCompareB,
  compareRes,
  compareLoading,
  runCompare,
}: {
  shoes: Shoe[];
  compareA: number | null;
  compareB: number | null;
  setCompareA: (v: number | null) => void;
  setCompareB: (v: number | null) => void;
  compareRes: AnalysisCompare | null;
  compareLoading: boolean;
  runCompare: () => void;
}) {
  const shoeA = compareA ? shoes.find(s => s.id === compareA) : null;
  const shoeB = compareB ? shoes.find(s => s.id === compareB) : null;

  return (
    <div className="rounded-card border border-border bg-card p-4">
      <h3 className="font-semibold mb-3">Comparação pareada</h3>

      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        <div className="flex-1">
          <label className="block text-xs text-muted mb-1">Tênis A</label>
          <select
            value={compareA ?? ""}
            onChange={e => setCompareA(Number(e.target.value) || null)}
            className="w-full rounded-ctl border border-border bg-raised px-3 py-2 text-sm focus:border-lime focus:outline-none focus:ring-1 focus:ring-lime"
          >
            <option value="">Selecione...</option>
            {shoes.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </div>
        <div className="flex-1">
          <label className="block text-xs text-muted mb-1">Tênis B</label>
          <select
            value={compareB ?? ""}
            onChange={e => setCompareB(Number(e.target.value) || null)}
            className="w-full rounded-ctl border border-border bg-raised px-3 py-2 text-sm focus:border-lime focus:outline-none focus:ring-1 focus:ring-lime"
          >
            <option value="">Selecione...</option>
            {shoes.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </div>
        <button
          onClick={runCompare}
          disabled={!compareA || !compareB || compareLoading}
          className="self-end rounded-full px-4 py-2 text-sm font-medium bg-lime/15 text-lime border border-lime/30 hover:bg-lime/25 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {compareLoading ? "Comparando..." : "Comparar"}
        </button>
      </div>

      {compareRes && (
        <div className="space-y-3">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-3 text-sm">
              <span className="text-muted">Pares válidos:</span>
              <span className="font-medium num text-text">{compareRes.n_pairs}</span>
              <ConfidenceBadge level={compareRes.confidence} />
            </div>
          </div>

          {compareRes.pairs.length === 0 ? (
            <div className="rounded-lg border border-border bg-raised/30 p-6 text-center">
              <p className="text-muted">Sem pares válidos entre estes tênis.</p>
              <p className="text-xs text-muted mt-1">Critério: distância ±5% e pace ±5%. Data livre.</p>
            </div>
          ) : (
            <div className="rounded-lg border border-border bg-raised/30 overflow-hidden">
              <div className="grid grid-cols-7 gap-1 bg-night/50 px-3 py-2 text-xs font-medium text-muted num">
                <div>Distância</div>
                <div className="text-center">Pace A</div>
                <div className="text-center">Pace B</div>
                <div className="text-center">Δ pace</div>
                <div className="text-center">FC A</div>
                <div className="text-center">FC B</div>
                <div className="text-center">Δ FC</div>
              </div>
              <div className="divide-y divide-border">
                {compareRes.pairs.map((p, i) => (
                  <div key={i} className="grid grid-cols-7 gap-1 px-3 py-2 text-sm hover:bg-raised/50 transition-colors">
                    <div className="flex items-center num text-text">{formatKm(p.distance_m)}</div>
                    <div className="flex items-center justify-center num text-text">{formatPace(p.pace_a_s)}/km</div>
                    <div className="flex items-center justify-center num text-text">{formatPace(p.pace_b_s)}/km</div>
                    <div className={`flex items-center justify-center num font-medium ${p.delta_pace_s > 0 ? "text-coral" : "text-lime"}`}>
                      {p.delta_pace_s > 0 ? "+" : ""}{p.delta_pace_s}s
                    </div>
                    <div className="flex items-center justify-center num text-text">{p.fc_a ?? "—"}</div>
                    <div className="flex items-center justify-center num text-text">{p.fc_b ?? "—"}</div>
                    <div className={`flex items-center justify-center num font-medium ${p.delta_fc && p.delta_fc > 0 ? "text-coral" : p.delta_fc && p.delta_fc < 0 ? "text-lime" : "text-text"}`}>
                      {p.delta_fc !== null && p.delta_fc !== undefined ? (p.delta_fc > 0 ? "+" : "") + p.delta_fc : "—"}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function DegradationView({ degradation, degradationLoading, shoeName }: {
  degradation: DegradationOut | null;
  degradationLoading: boolean;
  shoeName: string;
}) {
  return (
    <div className="rounded-card border border-border bg-card p-4">
      <div className="mb-3 flex items-baseline justify-between gap-3 flex-wrap">
        <h3 className="font-semibold">Alerta de degradação</h3>
        {degradation && !degradation.insufficient && (
          <div className="flex items-center gap-2 text-sm text-muted num">
            <span>{degradation.n_signals} sinais</span>
            <span>·</span>
            <span>{formatKm(degradation.total_km * 1000)}</span>
            <span>·</span>
            <span>{degradation.n_runs ?? 0} corridas</span>
          </div>
        )}
      </div>

      {degradationLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-12 w-full rounded-card" />
          <Skeleton className="h-12 w-full rounded-card" />
          <Skeleton className="h-12 w-full rounded-card" />
        </div>
      ) : degradation?.insufficient ? (
        <div className="rounded-lg border border-border bg-raised/30 p-6 text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-amber/15 text-amber mb-3">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <p className="font-medium">Dados insuficientes para degradação</p>
          <p className="text-sm text-muted mt-1">Mínimo ~150 km acumulados para análise (tem {degradation.total_km.toFixed(1)} km).</p>
        </div>
      ) : degradation ? (
        degradation.signals.length === 0 ? (
          <div className="rounded-lg border border-border bg-raised/30 p-6 text-center">
            <p className="text-muted">Nenhum sinal de degradação detectado.</p>
            <p className="text-xs text-muted mt-1">O tênis mantém comportamento estável nas métricas analisadas.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {degradation.signals.map((s, i) => (
              <SignalRow key={i} signal={s} />
            ))}
            <p className="text-xs text-muted text-center mt-2">
              Sinais, não veredito — sem recomendação de aposentadoria.
            </p>
          </div>
        )
      ) : (
        <p className="text-sm text-muted text-center py-4">Sem dados de degradação.</p>
      )}
    </div>
  );
}

function ViewTabs({
  activeView,
  setActiveView,
  shoes,
  selectedId,
  profiles,
  compareA,
  compareB,
  setCompareA,
  setCompareB,
  compareRes,
  compareLoading,
  runCompare,
  degradation,
  degradationLoading,
}: {
  activeView: ViewMode;
  setActiveView: (v: ViewMode) => void;
  shoes: Shoe[];
  selectedId: number | null;
  profiles: Map<number, AnalysisShoeProfile>;
  compareA: number | null;
  compareB: number | null;
  setCompareA: (v: number | null) => void;
  setCompareB: (v: number | null) => void;
  compareRes: AnalysisCompare | null;
  compareLoading: boolean;
  runCompare: () => void;
  degradation: DegradationOut | null;
  degradationLoading: boolean;
}) {
  const selectedShoe = shoes.find(s => s.id === selectedId) ?? shoes[0];
  const profile = selectedShoe ? profiles.get(selectedShoe.id) : undefined;

  const tabs: { id: ViewMode; label: string }[] = [
    { id: "perfil", label: "Perfil" },
    { id: "comparacao", label: "Comparação" },
    { id: "degradacao", label: "Degradação" },
  ];

  return (
    <div className="md:col-span-2 space-y-4">
      <div className="flex gap-1 bg-raised/50 rounded-ctl p-1">
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setActiveView(t.id)}
            className={`flex-1 rounded-ctl px-3 py-2 text-sm font-medium transition-colors ${
              activeView === t.id
                ? "bg-lime/15 text-lime"
                : "text-muted hover:text-text"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {activeView === "perfil" && profile && <ProfileCard profile={profile} shoeName={selectedShoe.name} />}
      {activeView === "perfil" && !profile && (
        <div className="rounded-card border border-border bg-card p-6 text-center">
          <p className="text-muted">Sem dados de análise para "{selectedShoe.name}".</p>
        </div>
      )}

      {activeView === "comparacao" && (
        <ComparisonView
          shoes={shoes}
          compareA={compareA}
          compareB={compareB}
          setCompareA={setCompareA}
          setCompareB={setCompareB}
          compareRes={compareRes}
          compareLoading={compareLoading}
          runCompare={runCompare}
        />
      )}

      {activeView === "degradacao" && (
        <DegradationView
          degradation={degradation}
          degradationLoading={degradationLoading}
          shoeName={selectedShoe.name}
        />
      )}
    </div>
  );
}

export default function ShoesAnalysisSection() {
  const [state, setState] = useState<PanelState>({ kind: "loading" });
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [activeView, setActiveView] = useState<ViewMode>("perfil");
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

  if (state.kind === "loading") {
    return (
      <PanelSection
        index={6}
        title="Análise de tênis"
        subtitle="Perfil por tipo × banda, comparação pareada e alerta de degradação"
      >
        <div className="space-y-3">
          <Skeleton className="h-10 w-48 rounded-ctl" />
          <div className="grid gap-3 sm:grid-cols-2">
            <Skeleton className="h-40 w-full rounded-card" />
            <Skeleton className="h-40 w-full rounded-card" />
          </div>
        </div>
      </PanelSection>
    );
  }

  if (state.kind === "error") {
    return (
      <PanelSection
        index={6}
        title="Análise de tênis"
        subtitle="Perfil por tipo × banda, comparação pareada e alerta de degradação"
      >
        <div className="rounded-card border border-destructive/30 bg-destructive/10 p-4">
          <p className="text-sm text-destructive">{state.message}</p>
        </div>
      </PanelSection>
    );
  }

  if (state.kind === "empty") {
    return (
      <PanelSection
        index={6}
        title="Análise de tênis"
        subtitle="Perfil por tipo × banda, comparação pareada e alerta de degradação"
      >
        <div className="rounded-card border border-border bg-card p-8 text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-raised mb-4">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-muted">
              <path d="M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z" />
              <path d="M12 8v4l2 2" />
            </svg>
          </div>
          <p className="font-medium mb-1">Nenhum tênis para analisar</p>
          <p className="text-sm text-muted mb-4">Cadastre um tênis e registre corridas com ele para ver o perfil, comparar e monitorar degradação.</p>
        </div>
      </PanelSection>
    );
  }

  const { shoes, profiles } = state;
  const selectedShoe = shoes.find(s => s.id === selectedId) ?? shoes[0];

  return (
    <PanelSection
      index={6}
      title="Análise de tênis"
      subtitle="Perfil por tipo × banda, comparação pareada e alerta de degradação"
    >
      <div className="grid gap-4 md:grid-cols-3">
        {/* Sidebar - lista de tênis */}
        <div className="md:col-span-1 space-y-2">
          {shoes.map(s => (
            <button
              key={s.id}
              onClick={() => {
                setSelectedId(s.id);
                setActiveView("perfil");
                setCompareA(null);
                setCompareB(null);
                setCompareRes(null);
              }}
              className={`w-full rounded-card border px-4 py-3 text-left transition-all ${
                selectedId === s.id
                  ? "border-lime bg-lime/5 shadow-[0_0_0_1px_var(--color-lime)]"
                  : "border-border bg-card hover:border-border-hover hover:bg-raised/30"
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">{s.name}</p>
                  <p className="text-xs text-muted flex items-center gap-1">
                    <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${
                      s.status === "ativo"
                        ? "bg-lime/15 text-lime"
                        : "bg-muted/20 text-muted"
                    }`}>
                      {s.status}
                    </span>
                    <span>{s.current_km.toFixed(1)} km</span>
                  </p>
                </div>
                {selectedId === s.id && (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-lime shrink-0">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                )}
              </div>
            </button>
          ))}
        </div>

        {/* Content area */}
        <ViewTabs
          activeView={activeView}
          setActiveView={setActiveView}
          shoes={shoes}
          selectedId={selectedId}
          profiles={profiles}
          compareA={compareA}
          compareB={compareB}
          setCompareA={setCompareA}
          setCompareB={setCompareB}
          compareRes={compareRes}
          compareLoading={compareLoading}
          runCompare={runCompare}
          degradation={degradation}
          degradationLoading={degradationLoading}
        />
      </div>
    </PanelSection>
  );
}