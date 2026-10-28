"use client";

// Modal de seleção de tênis — overlay fixed inset-0 z-50 + backdrop-blur
// (referência visual: TabBar). Ordenação: padrão-do-tipo
// (localStorage "shoe-default-by-type"[inferredType]) → last_use desc.
// Aposentados em bloco separado. Ações: escolher, "Definir como padrão para [tipo]", "Agora não".

import { useEffect, useState } from "react";

import { getShoes, setActivityShoe, type Shoe, type ShoeSummary } from "@/lib/api";
import { formatKm, formatDateTime } from "@/lib/format";

type ShoePickerModalProps = {
  activityId: number;
  inferredType: string | null;
  onAssigned: (shoe: ShoeSummary) => void;
  onDismiss: () => void;
};

const TYPE_LABELS: Record<string, string> = {
  prova: "Prova",
  intervalado: "Intervalado",
  limiar: "Limiar",
  tempo: "Tempo",
  progressivo: "Progressivo",
  longao: "Longão",
  facil: "Fácil",
};

function formatInferredType(type: string | null): string {
  if (!type) return "Corrida";
  return TYPE_LABELS[type] ?? type;
}

export default function ShoePickerModal({
  activityId,
  inferredType,
  onAssigned,
  onDismiss,
}: ShoePickerModalProps) {
  const [shoes, setShoes] = useState<Shoe[]>([]);
  const [loading, setLoading] = useState(true);
  const [defaultByType, setDefaultByType] = useState<Record<string, number>>({});

  // Carrega preferências do localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem("shoe-default-by-type");
      if (stored) {
        setDefaultByType(JSON.parse(stored));
      }
    } catch {
      // Ignora erro de parse
    }
  }, []);

  // Busca tênis
  useEffect(() => {
    getShoes()
      .then((data) => {
        setShoes(data.items);
        setLoading(false);
      })
      .catch(() => {
        setLoading(false);
      });
  }, []);

  // Separa ativos e aposentados, ordena
  const activeShoes = shoes.filter((s) => s.status === "ativo");
  const retiredShoes = shoes.filter((s) => s.status === "aposentado");

  const defaultShoeId = inferredType ? defaultByType[inferredType] : null;

  const sortShoes = (shoeList: Shoe[]) => {
    return [...shoeList].sort((a, b) => {
      // Padrão do tipo primeiro
      const aIsDefault = a.id === defaultShoeId;
      const bIsDefault = b.id === defaultShoeId;
      if (aIsDefault && !bIsDefault) return -1;
      if (!aIsDefault && bIsDefault) return 1;
      // Depois por last_use desc
      const aTime = a.last_use ? new Date(a.last_use).getTime() : 0;
      const bTime = b.last_use ? new Date(b.last_use).getTime() : 0;
      return bTime - aTime;
    });
  };

  const sortedActive = sortShoes(activeShoes);
  const sortedRetired = sortShoes(retiredShoes);

  const handleChoose = async (shoe: Shoe) => {
    try {
      const result = await setActivityShoe(activityId, shoe.id);
      if (result.shoe) {
        onAssigned(result.shoe);
      }
    } catch (err) {
      console.error("Erro ao associar tênis:", err);
    }
  };

  const handleSetDefault = (shoe: Shoe) => {
    if (!inferredType) return;
    const newDefaults = { ...defaultByType, [inferredType]: shoe.id };
    setDefaultByType(newDefaults);
    localStorage.setItem("shoe-default-by-type", JSON.stringify(newDefaults));
  };

  const handleDismiss = () => {
    onDismiss();
  };

  const typeLabel = inferredType ? formatInferredType(inferredType) : "Corrida";

  if (loading) {
    return (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm"
        onClick={handleDismiss}
        role="dialog"
        aria-modal="true"
        aria-label="Selecionar tênis"
      >
        <div className="w-full max-w-md mx-4 bg-background rounded-card border border-border p-6">
          <div className="space-y-3">
            <div className="h-6 w-1/3 skeleton rounded-ctl" />
            <div className="h-40 w-full skeleton rounded-card" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm"
      onClick={handleDismiss}
      role="dialog"
      aria-modal="true"
      aria-label="Selecionar tênis"
    >
      <div
        className="w-full max-w-md mx-4 bg-background rounded-card border border-border overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <h2 className="font-semibold">Qual tênis foi usado?</h2>
          <p className="text-sm text-muted">{typeLabel}</p>
        </div>

        {/* Lista de tênis ativos */}
        {sortedActive.length > 0 && (
          <div className="p-4">
            <h3 className="text-xs font-medium text-muted uppercase tracking-wider mb-3">
              Tênis ativos
            </h3>
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {sortedActive.map((shoe) => (
                <ShoeModalItem
                  key={shoe.id}
                  shoe={shoe}
                  isDefault={shoe.id === defaultShoeId}
                  inferredType={inferredType}
                  onChoose={() => handleChoose(shoe)}
                  onSetDefault={() => handleSetDefault(shoe)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Lista de tênis aposentados */}
        {sortedRetired.length > 0 && (
          <div className="border-t border-border px-4 py-4">
            <h3 className="text-xs font-medium text-muted uppercase tracking-wider mb-3">
              Aposentados (atribuição retroativa)
            </h3>
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {sortedRetired.map((shoe) => (
                <ShoeModalItem
                  key={shoe.id}
                  shoe={shoe}
                  isDefault={false}
                  inferredType={inferredType}
                  isRetired={true}
                  onChoose={() => handleChoose(shoe)}
                  onSetDefault={() => {}}
                />
              ))}
            </div>
          </div>
        )}

        {/* Estado vazio */}
        {sortedActive.length === 0 && sortedRetired.length === 0 && (
          <div className="p-6 text-center text-muted">
            <p className="mb-3">Nenhum tênis cadastrado.</p>
            <p className="text-sm">Cadastre um tênis na seção Tênis da página Treinos.</p>
          </div>
        )}

        {/* Footer */}
        <div className="border-t border-border px-4 py-3 flex items-center justify-end gap-2">
          <button
            onClick={handleDismiss}
            className="rounded-full border border-border bg-card px-4 py-2 text-sm font-medium text-foreground hover:bg-accent/10 transition-colors"
          >
            Agora não
          </button>
        </div>
      </div>
    </div>
  );
}

function ShoeModalItem({
  shoe,
  isDefault,
  inferredType,
  isRetired = false,
  onChoose,
  onSetDefault,
}: {
  shoe: Shoe;
  isDefault: boolean;
  inferredType: string | null;
  isRetired?: boolean;
  onChoose: () => void;
  onSetDefault: () => void;
}) {
  const lifePct = shoe.life_pct ?? 0;

  return (
    <div
      className={`relative rounded-card border border-border bg-card p-3 ${
        isDefault ? "ring-2 ring-accent" : ""
      } ${isRetired ? "opacity-60" : ""}`}
    >
      {isDefault && (
        <span className="absolute -top-2 -right-2 rounded-full bg-accent/15 px-1.5 py-0.5 text-xs font-medium text-accent">
          Padrão
        </span>
      )}

      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2 flex-wrap">
            <h4 className="font-medium truncate">{shoe.name}</h4>
            {shoe.brand && (
              <span className="text-sm text-muted">{shoe.brand}</span>
            )}
            {shoe.model && (
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

          {shoe.max_km && shoe.max_km > 0 && (
            <div className="mt-2">
              <div className="flex items-center justify-between text-xs text-muted mb-1">
                <span>
                  {formatKm(shoe.current_km * 1000)} / {formatKm(shoe.max_km * 1000)}
                </span>
                <span>{Math.round(lifePct)}%</span>
              </div>
              <div className="relative h-2 w-full overflow-hidden rounded-full bg-border">
                <div
                  className="h-full transition-all duration-300"
                  style={{
                    width: `${Math.min(lifePct, 100)}%`,
                    backgroundColor:
                      lifePct >= 90
                        ? "var(--color-destructive)"
                        : lifePct >= 75
                        ? "var(--color-warning)"
                        : "var(--color-accent)",
                  }}
                />
                <div className="absolute top-0 bottom-0 left-[75%] w-px bg-background/50" />
                <div className="absolute top-0 bottom-0 left-[90%] w-px bg-background/50" />
              </div>
            </div>
          )}

          <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-muted">
            {shoe.run_count > 0 && (
              <span>
                {shoe.run_count} {shoe.run_count === 1 ? "corrida" : "corridas"}
              </span>
            )}
            {shoe.last_use && (
              <span>Último: {formatDateTime(shoe.last_use)}</span>
            )}
          </div>
        </div>

        <div className="flex flex-col items-end gap-1 shrink-0">
          {!isRetired && (
            <button
              onClick={onChoose}
              className="rounded-full bg-accent px-3 py-1.5 text-sm font-medium text-accent-foreground hover:bg-accent/90 transition-colors"
            >
              Escolher
            </button>
          )}
          {!isRetired && inferredType && !isDefault && (
            <button
              onClick={onSetDefault}
              className="rounded-full border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground hover:bg-accent/10 transition-colors whitespace-nowrap"
            >
              Definir como padrão para {formatInferredType(inferredType ?? "")}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}