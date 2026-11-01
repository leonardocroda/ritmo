"use client";

import { useState } from "react";
import { Shoe } from "@/lib/api";
import { updateShoe, type ShoeUpdate } from "@/lib/api";

interface ShoeEditFormProps {
  shoe: Shoe;
  onSave: (data: ShoeUpdate) => void | Promise<void>;
  onCancel: () => void;
}

export function ShoeEditForm({ shoe, onSave, onCancel }: ShoeEditFormProps) {
  const isEditing = true;
  const [name, setName] = useState(shoe?.name ?? "");
  const [brand, setBrand] = useState(shoe?.brand && shoe.brand !== "undefined" && shoe.brand !== "null" ? shoe.brand : "");
  const [model, setModel] = useState(shoe?.model && shoe.model !== "undefined" && shoe.model !== "null" ? shoe.model : "");
  const [acquired_date, setAcquiredDate] = useState(
    shoe?.acquired_date?.split("T")[0] ?? "",
  );
  const [initial_km, setInitialKm] = useState(shoe?.initial_km ?? 0);
  const [max_km, setMaxKm] = useState<string | number>(
    shoe?.max_km ?? "",
  );
  const [status, setStatus] = useState<"ativo" | "aposentado">(
    shoe?.status ?? "ativo",
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSaving(true);
    const maxKmValue = max_km === "" ? null : Number(max_km);
    const data: ShoeUpdate = {
      name: name.trim(),
      brand: brand.trim() || null,
      model: model.trim() || null,
      acquired_date: acquired_date || null,
      initial_km,
      max_km: maxKmValue,
      status,
    };
    try {
      await onSave(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao salvar");
    } finally {
      setSaving(false);
    }
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
          <label className="block text-sm font-medium mb-1">Vida útil estimada (km)</label>
          <input
            type="number"
            min="0"
            step="10"
            value={max_km}
            onChange={(e) =>
              setMaxKm(e.target.value === "" ? "" : Number(e.target.value))
            }
            className="w-full rounded-ctl border border-border bg-card px-3 py-2 text-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
            placeholder="800"
          />
        </div>

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
      </div>

      {error && (
        <div className="rounded-card border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="mt-4 flex items-center gap-2">
        <button
          type="submit"
          disabled={saving}
          className="rounded-full bg-accent px-4 py-2 text-sm font-medium text-on-accent hover:bg-accent/90 transition-colors disabled:opacity-50"
        >
          {saving ? "Salvando..." : "Salvar"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={saving}
          className="rounded-full border border-border bg-card px-4 py-2 text-sm font-medium text-foreground hover:bg-accent/10 transition-colors disabled:opacity-50"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}