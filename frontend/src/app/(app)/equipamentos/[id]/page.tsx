"use client";

import { useEffect, useState } from "react";
import { notFound } from "next/navigation";
import Link from "next/link";
import { formatKm } from "@/lib/format";
import { getShoes, updateShoe, type Shoe, type ShoeUpdate, type ShoesOut } from "@/lib/api";
import { useShoeAnalysis } from "@/hooks/shoes/useShoeAnalysis";
import { useShoeDegradation } from "@/hooks/shoes/useShoeDegradation";
import { DetailTabs } from "@/components/workouts/shoes/detail/DetailTabs";
import { ShoeEditForm } from "@/components/workouts/shoes/detail/ShoeEditForm";
import Skeleton from "@/components/Skeleton";
import PanelSection from "@/components/PanelSection";

type ViewMode = "overview" | "degradation";

interface ShoeDetailPageState {
  shoe: Shoe | null;
  loading: boolean;
  error: string | null;
  activeView: ViewMode;
  showEditForm: boolean;
}

export default function ShoeDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const [state, setState] = useState<ShoeDetailPageState>({
    shoe: null,
    loading: true,
    error: null,
    activeView: "overview",
    showEditForm: false,
  });

  // Hooks
  const { profiles, loading: analysisLoading, error: analysisError, refetch: refetchAnalysis } = useShoeAnalysis();
  const { degradation, enrichedSignals, loading: degradationLoading, error: degradationError, refetch: refetchDegradation } = useShoeDegradation();

  // Load shoe by ID
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const resolvedParams = await params;
      const shoeId = parseInt(resolvedParams.id, 10);
      try {
        const data: ShoesOut = await getShoes();
        const shoe = data.items.find(s => s.id === shoeId);
        if (!cancelled) {
          if (shoe) {
            setState(prev => ({ ...prev, shoe, loading: false, activeView: "overview", showEditForm: false }));
          } else {
            notFound();
          }
        }
      } catch (err) {
        if (!cancelled) {
          setState({ shoe: null, loading: false, error: err instanceof Error ? err.message : "Erro ao carregar tênis", activeView: "overview", showEditForm: false });
        }
      }
    })();
    return () => { cancelled = true; };
  }, [params]);

  // Sync degradation refetch when shoe changes
  useEffect(() => {
    if (state.shoe) {
      refetchDegradation(state.shoe.id);
    }
  }, [state.shoe, refetchDegradation]);

  const handleSetActiveView = (v: ViewMode) => setState(prev => ({ ...prev, activeView: v }));
  const handleOpenEdit = () => setState(prev => ({ ...prev, showEditForm: true }));
  const handleCloseEdit = () => setState(prev => ({ ...prev, showEditForm: false }));
  const handleSaveEdit = async (data: ShoeUpdate) => {
    if (!state.shoe) return;
    try {
      const { updateShoe } = await import("@/lib/api");
      await updateShoe(state.shoe.id, data);
      // Refresh shoe list and analysis
      const { getShoes } = await import("@/lib/api");
      const fresh = await getShoes();
      const updatedShoe = fresh.items.find(s => s.id === state.shoe!.id);
      if (updatedShoe) {
        setState(prev => ({ ...prev, shoe: updatedShoe, showEditForm: false }));
      }
      refetchAnalysis();
      refetchDegradation(state.shoe.id);
    } catch (err) {
      console.error("Failed to update shoe:", err);
    }
  };

  // Loading state
  if (state.loading) {
    return (
      <PanelSection title="Carregando..." subtitle="">
        <Skeleton className="h-10 w-48 rounded-ctl" />
        <div className="mt-4 space-y-3">
          <Skeleton className="h-32 w-full rounded-card" />
          <Skeleton className="h-32 w-full rounded-card" />
        </div>
      </PanelSection>
    );
  }

  // Error state
  if (state.error || !state.shoe) {
    return (
      <PanelSection title="Erro" subtitle="">
        <div className="rounded-card border border-destructive/30 bg-destructive/10 p-4 text-center">
          <p className="text-sm text-destructive">{state.error || "Tênis não encontrado"}</p>
          <Link href="/equipamentos" className="mt-3 inline-block text-sm underline">
            Voltar para equipamentos
          </Link>
        </div>
      </PanelSection>
    );
  }

  const shoe = state.shoe!;
  const profile = profiles.get(shoe.id);

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-6 sm:px-6 pb-20">
      <div className="space-y-6">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm text-muted" aria-label="Breadcrumb">
          <Link href="/equipamentos" className="hover:text-text">Equipamentos</Link>
          <span>/</span>
          <Link href="/equipamentos" className="hover:text-text">Tênis</Link>
          <span>/</span>
          <span className="text-text font-medium truncate max-w-[200px]">{shoe.name}</span>
        </nav>

      {/* Header with edit button */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-semibold">{shoe.name}</h1>
          <div className="flex items-center gap-2 mt-1 text-sm text-muted">
            {shoe.brand && <span>{shoe.brand}</span>}
            {shoe.model && <span>· {shoe.model}</span>}
            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
              shoe.status === "ativo" ? "bg-lime/15 text-lime" : "bg-muted/20 text-muted"
            }`}>
              {shoe.status === "ativo" ? "Ativo" : "Aposentado"}
            </span>
          </div>
        </div>
        <button
          onClick={handleOpenEdit}
          className="rounded-full border border-border bg-card px-4 py-2 text-sm font-medium text-foreground hover:bg-accent/10 transition-colors"
        >
          Editar
        </button>
      </div>

      {/* Life bar */}
      {shoe.max_km && shoe.max_km > 0 && (
        <div className="rounded-card border border-border bg-card p-4">
          <div className="flex items-center justify-between text-xs text-muted mb-1">
            <span>
              {formatKm(shoe.current_km * 1000)} / {formatKm(shoe.max_km * 1000)}
            </span>
            <span>{shoe.life_pct ? Math.round(shoe.life_pct) : 0}%</span>
          </div>
          <div className="relative h-3 w-full overflow-hidden rounded-full bg-border">
            <div
              className="h-full transition-all duration-300"
              style={{
                width: `${Math.min(shoe.life_pct ?? 0, 100)}%`,
                backgroundColor:
                  (shoe.life_pct ?? 0) >= 90
                    ? "var(--color-alert)"
                    : (shoe.life_pct ?? 0) >= 75
                    ? "var(--color-attention)"
                    : "var(--color-good)",
              }}
            />
            <div className="absolute top-0 bottom-0 left-[75%] w-px bg-background/50" />
            <div className="absolute top-0 bottom-0 left-[90%] w-px bg-background/50" />
          </div>
        </div>
      )}

      {/* Meta info */}
      <div className="flex flex-wrap items-center gap-4 text-xs text-muted">
        {shoe.run_count > 0 && (
          <span>{shoe.run_count} {shoe.run_count === 1 ? "corrida" : "corridas"}</span>
        )}
        {shoe.last_use && (
          <span>Último uso: {new Date(shoe.last_use).toLocaleDateString("pt-BR")}</span>
        )}
        {shoe.acquired_date && (
          <span>Desde: {shoe.acquired_date.split("T")[0]}</span>
        )}
      </div>

      {/* Tabs with content */}
      <DetailTabs
        activeView={state.activeView}
        onChange={handleSetActiveView}
        shoe={shoe}
        profile={profile}
        degradation={degradation}
        enrichedSignals={enrichedSignals}
        degradationLoading={degradationLoading}
        degradationError={degradationError}
        analysisLoading={analysisLoading}
        analysisError={analysisError}
      />

      {/* Edit modal */}
      {state.showEditForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="w-full max-w-md bg-card rounded-xl p-6 shadow-xl">
            <ShoeEditForm
              shoe={shoe}
              onSave={handleSaveEdit}
              onCancel={handleCloseEdit}
            />
          </div>
        </div>
      )}
    </div>
  </main>
  );
}