"use client";

// Seção Tênis na página Treinos — gestão de tênis com barra de vida útil,
// criar/editar inline, aposentar com confirmação e badge de higiene (30d).
// Padrão PanelState (loading/error/empty/ready) igual a HomePanel.

import { useEffect, useState } from "react";

import { getShoes, createShoe, updateShoe, type Shoe, type ShoeCreate, type ShoeUpdate, type ShoesOut } from "@/lib/api";
import PanelSection from "@/components/PanelSection";
import Skeleton from "@/components/Skeleton";
import { formatKm, formatDateTime } from "@/lib/format";

type PanelState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "empty" }
  | { kind: "ready"; data: ShoesOut };

function ShoeCard({
  shoe,
  onEdit,
  onRetire,
}: {
  shoe: Shoe;
  onEdit: (shoe: Shoe) => void;
  onRetire: (shoe: Shoe) => void;
}) {
  const lifePct = shoe.life_pct ?? 0;
  const isRetired = shoe.status === "aposentado";

  return (
    <div className="rounded-card border border-border bg-card p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2 flex-wrap">
            <h3 className="font-medium truncate">{shoe.name}</h3>
            {shoe.brand && shoe.brand !== "undefined" && shoe.brand !== "null" && (
              <span className="text-sm text-muted">{shoe.brand}</span>
            )}
            {shoe.model && shoe.model !== "undefined" && shoe.model !== "null" && (
              <span className="text-sm text-muted">{shoe.model}</span>
            )}
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                isRetired
                  ? "bg-muted/20 text-muted"
                  : "bg-accent/15 text-accent"
              }`}
            >
              {shoe.status === "ativo" ? "Ativo" : "Aposentado"}
            </span>
          </div>

          {/* Barra de vida útil */}
          {shoe.max_km && shoe.max_km > 0 && (
            <div className="mt-3">
              <div className="flex items-center justify-between text-xs text-muted mb-1">
                <span>
                  {formatKm(shoe.current_km * 1000)} / {formatKm(shoe.max_km * 1000)}
                </span>
                <span>{Math.round(lifePct)}%</span>
              </div>
              <div className="relative h-3 w-full overflow-hidden rounded-full bg-border">
                <div
                  className="h-full transition-all duration-300"
                  style={{
                    width: `${Math.min(lifePct, 100)}%`,
                    backgroundColor:
                      lifePct >= 90
                        ? "var(--color-alert)"
                        : lifePct >= 75
                        ? "var(--color-attention)"
                        : "var(--color-good)",
                  }}
                />
                {/* Marcas 75% e 90% */}
                <div className="absolute top-0 bottom-0 left-[75%] w-px bg-background/50" />
                <div className="absolute top-0 bottom-0 left-[90%] w-px bg-background/50" />
              </div>
            </div>
          )}

          <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-muted">
            {shoe.run_count > 0 && (
              <span>
                {shoe.run_count} {shoe.run_count === 1 ? "corrida" : "corridas"}
              </span>
            )}
            {shoe.last_use && (
              <span>Último uso: {formatDateTime(shoe.last_use)}</span>
            )}
            {shoe.acquired_date && (
              <span>Desde: {shoe.acquired_date.split("T")[0]}</span>
            )}
          </div>
        </div>

        <div className="flex flex-col items-end gap-1 shrink-0">
          {!isRetired && (
            <button
              onClick={() => onRetire(shoe)}
              className="rounded-full border border-destructive/30 bg-destructive/10 px-3 py-1.5 text-sm font-medium text-destructive hover:bg-destructive/20 transition-colors"
            >
              Aposentar
            </button>
          )}
          <button
            onClick={() => onEdit(shoe)}
            className="rounded-full border border-border bg-card px-3 py-1.5 text-sm font-medium text-foreground hover:bg-accent/10 transition-colors"
          >
            Editar
          </button>
        </div>
      </div>
    </div>
  );
}

function ShoeForm({
  shoe,
  onSubmit,
  onCancel,
}: {
  shoe: Shoe | null;
  onSubmit: (data: { name: string; brand?: string | null; model?: string | null; acquired_date?: string | null; initial_km?: number; max_km?: number | null; status?: "ativo" | "aposentado" }) => void | Promise<void>;
  onCancel: () => void;
}) {
  const isEditing = shoe !== null;
  const [name, setName] = useState(shoe?.name ?? "");
  const [brand, setBrand] = useState(shoe?.brand && shoe.brand !== "undefined" && shoe.brand !== "null" ? shoe.brand : "");
  const [model, setModel] = useState(shoe?.model && shoe.model !== "undefined" && shoe.model !== "null" ? shoe.model : "");
  const [acquired_date, setAcquiredDate] = useState(
    shoe?.acquired_date?.split("T")[0] ?? "",
  );
  const [initial_km, setInitialKm] = useState(shoe?.initial_km ?? 0);
  const [max_km, setMaxKm] = useState<string | number>(
    shoe?.max_km ?? (isEditing ? "" : 800),
  );
  const [status, setStatus] = useState<"ativo" | "aposentado">(
    shoe?.status ?? "ativo",
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const maxKmValue = max_km === "" ? null : Number(max_km);
    const data: ShoeCreate = {
      name: name.trim(),
      brand: brand.trim() || null,
      model: model.trim() || null,
      acquired_date: acquired_date || null,
      initial_km,
      max_km: maxKmValue,
      status,
    };
    onSubmit(data);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <label className="block text-sm font-medium mb-1">Nome *</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded-ctl border border-border bg-card px-3 py-2 text-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
            required
            placeholder="Ex: Kayano 30"
            autoFocus
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Marca</label>
          <input
            type="text"
            value={brand}
            onChange={(e) => setBrand(e.target.value)}
            className="w-full rounded-ctl border border-border bg-card px-3 py-2 text-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
            placeholder="Ex: ASICS"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Modelo</label>
          <input
            type="text"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="w-full rounded-ctl border border-border bg-card px-3 py-2 text-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
            placeholder="Ex: Gel-Kayano 30"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Data de aquisição</label>
          <input
            type="date"
            value={acquired_date}
            onChange={(e) => setAcquiredDate(e.target.value)}
            className="w-full rounded-ctl border border-border bg-card px-3 py-2 text-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Km inicial</label>
          <input
            type="number"
            min="0"
            step="0.1"
            value={initial_km}
            onChange={(e) => setInitialKm(Number(e.target.value) || 0)}
            className="w-full rounded-ctl border border-border bg-card px-3 py-2 text-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
            placeholder="0"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">
            Vida útil estimada (km) {isEditing ? "" : "(sugere 800)"}
          </label>
          <input
            type="number"
            min="0"
            step="10"
            value={max_km}
            onChange={(e) =>
              setMaxKm(e.target.value === "" ? "" : Number(e.target.value))
            }
            className="w-full rounded-ctl border border-border bg-card px-3 py-2 text-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
            placeholder={isEditing ? "" : "800"}
          />
        </div>

        {isEditing && (
          <div className="sm:col-span-2">
            <label className="block text-sm font-medium mb-1">Status</label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value as "ativo" | "aposentado")}
              className="w-full rounded-ctl border border-border bg-card px-3 py-2 text-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
            >
              <option value="ativo">Ativo</option>
              <option value="aposentado">Aposentado</option>
            </select>
          </div>
        )}
      </div>

      <div className="mt-4 flex items-center gap-2">
        <button
          type="submit"
          className="rounded-full bg-accent px-4 py-2 text-sm font-medium text-on-accent hover:bg-accent/90 transition-colors"
        >
          {isEditing ? "Salvar" : "Criar tênis"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-full border border-border bg-card px-4 py-2 text-sm font-medium text-foreground hover:bg-accent/10 transition-colors"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}

export default function ShoesSection() {
  const [state, setState] = useState<PanelState>({ kind: "loading" });
  const [editingShoe, setEditingShoe] = useState<Shoe | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);

  useEffect(() => {
    getShoes()
      .then((data) => {
        if (data.items.length === 0) {
          setState({ kind: "empty" });
        } else {
          setState({ kind: "ready", data });
        }
      })
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : "Erro inesperado";
        setState({ kind: "error", message });
      });
  }, []);

  const handleCreate = async (data: ShoeCreate) => {
    try {
      await createShoe(data);
      setShowCreateForm(false);
      const fresh = await getShoes();
      setState(fresh.items.length === 0 ? { kind: "empty" } : { kind: "ready", data: fresh });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Erro ao criar tênis";
      setState({ kind: "error", message });
    }
  };

  const handleUpdate = async (data: ShoeUpdate) => {
    if (!editingShoe) return;
    try {
      await updateShoe(editingShoe.id, data);
      setEditingShoe(null);
      const fresh = await getShoes();
      setState(fresh.items.length === 0 ? { kind: "empty" } : { kind: "ready", data: fresh });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Erro ao atualizar tênis";
      setState({ kind: "error", message });
    }
  };

  const handleRetire = async (shoe: Shoe) => {
    if (!confirm(`Aposentar "${shoe.name}"? Ele permanece no histórico mas sai das sugestões.`)) {
      return;
    }
    try {
      await updateShoe(shoe.id, { status: "aposentado" });
      const fresh = await getShoes();
      setState(fresh.items.length === 0 ? { kind: "empty" } : { kind: "ready", data: fresh });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Erro ao aposentar tênis";
      setState({ kind: "error", message });
    }
  };

  const handleEdit = (shoe: Shoe) => {
    setEditingShoe(shoe);
  };

  const handleCancelEdit = () => {
    setEditingShoe(null);
  };

  const handleCancelCreate = () => {
    setShowCreateForm(false);
  };

  if (state.kind === "loading") {
    return (
      <PanelSection
        index={5}
        title="Tênis"
        subtitle="Gerencie seus tênis: quilometragem, vida útil e aposentadoria"
      >
        <div className="space-y-3">
          <Skeleton className="h-24 w-full rounded-card" />
          <Skeleton className="h-24 w-full rounded-card" />
          <Skeleton className="h-24 w-full rounded-card" />
        </div>
      </PanelSection>
    );
  }

  if (state.kind === "error") {
    return (
      <PanelSection
        index={5}
        title="Tênis"
        subtitle="Gerencie seus tênis: quilometragem, vida útil e aposentadoria"
      >
        <p className="rounded-card border border-border bg-card px-4 py-3 text-sm text-muted">
          Não foi possível carregar os tênis: {state.message}
        </p>
      </PanelSection>
    );
  }

  if (state.kind === "empty") {
    return (
      <PanelSection
        index={5}
        title="Tênis"
        subtitle="Gerencie seus tênis: quilometragem, vida útil e aposentadoria"
      >
        {showCreateForm && (
          <div className="mb-4 rounded-card border border-border bg-card p-4">
            <h4 className="mb-3 font-medium">Cadastrar tênis</h4>
            <ShoeForm shoe={null} onSubmit={handleCreate} onCancel={handleCancelCreate} />
          </div>
        )}
        <div className="rounded-card border border-border bg-card px-4 py-6 text-sm text-muted text-center">
          <p className="mb-3">Nenhum tênis cadastrado ainda.</p>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowCreateForm(true);
            }}
            className="rounded-full bg-accent px-4 py-2 text-sm font-medium text-on-accent hover:bg-accent/90 transition-colors cursor-pointer"
          >
            Cadastrar primeiro tênis
          </button>
        </div>
      </PanelSection>
    );
  }

  const { items, attribution_30d_pct } = state.data;

  return (
    <PanelSection
      index={5}
      title="Tênis"
      subtitle="Gerencie seus tênis: quilometragem, vida útil e aposentadoria"
      badge={
        attribution_30d_pct !== null
          ? `${Math.round(attribution_30d_pct)}% das corridas dos últimos 30 dias com tênis`
          : undefined
      }
    >
      {showCreateForm && (
        <div className="mb-4 rounded-card border border-border bg-card p-4">
          <h4 className="mb-3 font-medium">Cadastrar tênis</h4>
          <ShoeForm shoe={null} onSubmit={handleCreate} onCancel={handleCancelCreate} />
        </div>
      )}

      {editingShoe && (
        <div className="mb-4 rounded-card border border-border bg-card p-4">
          <h4 className="mb-3 font-medium">Editar "{editingShoe.name}"</h4>
          <ShoeForm shoe={editingShoe} onSubmit={handleUpdate} onCancel={handleCancelEdit} />
        </div>
      )}

      {!showCreateForm && !editingShoe && (
        <button
          onClick={() => setShowCreateForm(true)}
          className="mb-4 rounded-full bg-accent px-4 py-2 text-sm font-medium text-on-accent hover:bg-accent/90 transition-colors cursor-pointer"
        >
          + Cadastrar tênis
        </button>
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        {items.map((shoe) => (
          <ShoeCard
            key={shoe.id}
            shoe={shoe}
            onEdit={handleEdit}
            onRetire={handleRetire}
          />
        ))}
      </div>
    </PanelSection>
  );
}