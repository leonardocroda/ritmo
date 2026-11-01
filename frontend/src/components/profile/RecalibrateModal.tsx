"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

type RecalibrateModalProps = {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
};

const STANDARD_DISTANCES = [
  { label: "1500m", value: 1.5 },
  { label: "3K", value: 3.0 },
  { label: "5K", value: 5.0 },
  { label: "10K", value: 10.0 },
  { label: "Meia Maratona (21.1K)", value: 21.0975 },
  { label: "Maratona (42.2K)", value: 42.195 },
  { label: "Outra distância", value: null },
];

export default function RecalibrateModal({ isOpen, onClose, onSuccess }: RecalibrateModalProps) {
  // Fecha ao pressionar Escape
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }

    if (isOpen) {
      document.addEventListener("keydown", handleKeyDown);
    }
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  const [selectedDistance, setSelectedDistance] = useState<string>("10K");
  const [customDistance, setCustomDistance] = useState<string>("");
  const [timeStr, setTimeStr] = useState<string>("");
  const [testDate, setTestDate] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const distanceValue = STANDARD_DISTANCES.find((d) => d.label === selectedDistance)?.value;
  const showCustomInput = distanceValue === null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const distanceKm = showCustomInput ? parseFloat(customDistance.replace(",", ".")) : distanceValue!;
    
    if (!distanceKm || distanceKm <= 0) {
      setError("Distância inválida");
      setLoading(false);
      return;
    }

    if (!timeStr || !/^\d{1,2}:\d{2}(:\d{2})?$/.test(timeStr)) {
      setError("Tempo inválido. Use MM:SS ou HH:MM:SS");
      setLoading(false);
      return;
    }

    try {
      const res = await apiFetch("/api/profile/pace-zones/recalibrate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          distance_km: distanceKm,
          time_str: timeStr,
          test_date: testDate || undefined,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Erro ao recalibrar");
      }

      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro inesperado");
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Recalibrar VDOT"
    >
      <div
        className="w-full max-w-md mx-4 bg-background rounded-card border border-border overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <h2 className="font-semibold">Recalibrar VDOT</h2>
        </div>

        {/* Conteúdo */}
        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <p className="text-sm text-muted">
            Insira a distância e o tempo do seu último teste máximo para recalcular
            suas zonas de ritmo personalizadas.
          </p>

          {/* Distância */}
          <div className="space-y-2">
            <label htmlFor="distance" className="block text-sm font-medium">
              Distância do teste
            </label>
            <select
              id="distance"
              value={selectedDistance}
              onChange={(e) => setSelectedDistance(e.target.value)}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
            >
              {STANDARD_DISTANCES.map((d) => (
                <option key={d.label} value={d.label}>
                  {d.label}
                </option>
              ))}
            </select>

            {showCustomInput && (
              <div className="space-y-1">
                <label htmlFor="customDistance" className="block text-sm font-medium">
                  Distância personalizada (km)
                </label>
                <input
                  id="customDistance"
                  type="text"
                  value={customDistance}
                  onChange={(e) => setCustomDistance(e.target.value)}
                  placeholder="Ex: 8.5"
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                />
              </div>
            )}
          </div>

          {/* Tempo */}
          <div className="space-y-2">
            <label htmlFor="time" className="block text-sm font-medium">
              Tempo total
            </label>
            <input
              id="time"
              type="text"
              value={timeStr}
              onChange={(e) => setTimeStr(e.target.value)}
              placeholder="MM:SS ou HH:MM:SS (ex: 40:12 ou 00:40:12)"
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-accent"
              maxLength={8}
            />
            <p className="text-xs text-muted">Formato: MM:SS ou HH:MM:SS</p>
          </div>

          {/* Data do teste (opcional) */}
          <div className="space-y-2">
            <label htmlFor="testDate" className="block text-sm font-medium">
              Data do teste (opcional)
            </label>
            <input
              id="testDate"
              type="date"
              value={testDate}
              onChange={(e) => setTestDate(e.target.value)}
              max={new Date().toISOString().split("T")[0]}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
            />
            <p className="text-xs text-muted">Deixe em branco para usar hoje</p>
          </div>

          {error && (
            <div className="rounded-md bg-destructive/10 border border-destructive/20 p-3 text-sm text-destructive">
              {error}
            </div>
          )}

          <div className="border-t border-border pt-3 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-3 py-1.5 text-sm rounded-md bg-muted hover:bg-muted/80 transition-colors disabled:opacity-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-3 py-1.5 text-sm rounded-md bg-accent text-accent-foreground hover:bg-accent/90 transition-colors disabled:opacity-50"
            >
              {loading ? "Salvando..." : "Recalibrar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}