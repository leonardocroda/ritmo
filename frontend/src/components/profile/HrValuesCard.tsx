"use client";

// Seção 1 "Valores" do /perfil (feature hr-zones — HRZ-01/13/14): as
// três métricas fisiológicas (FC máxima, FC de repouso, LTHR) com
// input numérico, badge de fonte (Garmin/Manual) e vigência. Salvar →
// PUT updateHrZones({metrics}) com os campos preenchidos — a página
// re-renderiza da resposta (a fonte vira Manual, HRZ-02); valor igual
// ao vigente não cria linha (HRZ-03, idempotente). O 422 do backend
// chega "campo: motivo" em PT-BR e vira erro inline no input
// correspondente (HRZ-14); estado vazio é honesto — "nunca
// configurado" + orientação (sync preenche, ou digite e salve).

import { useState, type FormEvent } from "react";

import { ApiError, updateHrZones, type HrZonesOut } from "@/lib/api";

type MetricKind = keyof HrZonesOut["metrics"];

// Ordem de exibição — rótulo PT-BR por kind (a API usa ASCII).
const METRIC_FIELDS = [
  { kind: "fcmax", label: "FC máxima" },
  { kind: "fcrest", label: "FC de repouso" },
  { kind: "fclthr", label: "LTHR" },
] as const;

const INPUT_CLASS =
  "mt-1 w-full rounded-lg border border-white/10 bg-card px-3 py-2 text-sm text-foreground outline-none focus:border-accent/50";

/** "garmin" → "Garmin" — a API manda ASCII, a UI rotula. */
function sourceLabel(source: string): string {
  return source === "garmin" ? "Garmin" : "Manual";
}

/** valid_from ISO "2026-10-20" → "20/10/2026" (wall clock, sem fuso). */
function formatDate(iso: string): string {
  return iso.split("-").reverse().join("/");
}

function metricToStrings(metrics: HrZonesOut["metrics"]): Record<MetricKind, string> {
  return {
    fcmax: metrics.fcmax?.value.toString() ?? "",
    fcrest: metrics.fcrest?.value.toString() ?? "",
    fclthr: metrics.fclthr?.value.toString() ?? "",
  };
}

export default function HrValuesCard({
  metrics,
  onSaved,
}: {
  metrics: HrZonesOut["metrics"];
  onSaved: (out: HrZonesOut) => void;
}) {
  const [values, setValues] = useState<Record<MetricKind, string>>(() =>
    metricToStrings(metrics),
  );
  const [errors, setErrors] = useState<Partial<Record<MetricKind, string>>>({});
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const hasAnyInput =
    values.fcmax !== "" || values.fcrest !== "" || values.fclthr !== "";

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setGeneralError(null);
    const updates: { fcmax?: number; fcrest?: number; fclthr?: number } = {};
    const nextErrors: Partial<Record<MetricKind, string>> = {};
    for (const field of METRIC_FIELDS) {
      const raw = values[field.kind].trim();
      if (raw === "") continue; // vazio = não mexe na métrica
      const parsed = Number(raw);
      if (!Number.isInteger(parsed)) {
        nextErrors[field.kind] = "informe um número inteiro";
      } else {
        updates[field.kind] = parsed;
      }
    }
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;
    setSaving(true);
    try {
      const out = await updateHrZones({ metrics: updates });
      setValues(metricToStrings(out.metrics)); // inputs = verdade do servidor
      onSaved(out);
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) {
        // detail "campo: motivo" → inline no campo apontado (HRZ-14)
        const [field, ...rest] = err.message.split(": ");
        if (rest.length > 0 && field in values) {
          setErrors({ [field]: rest.join(": ") });
        } else {
          setGeneralError(err.message);
        }
      } else {
        setGeneralError(
          err instanceof Error
            ? err.message
            : "Não foi possível salvar. Tente de novo.",
        );
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSave}>
      <div className="grid gap-2 sm:grid-cols-3">
        {METRIC_FIELDS.map((field) => {
          const metric = metrics[field.kind];
          return (
            <div
              key={field.kind}
              className="rounded-xl border border-white/10 bg-card px-3 py-2"
            >
              <div className="flex items-baseline justify-between gap-2">
                <p className="text-sm font-medium">{field.label}</p>
                {metric !== null ? (
                  <span className="rounded-full bg-accent/15 px-2 py-0.5 text-xs font-medium text-accent">
                    {sourceLabel(metric.source)}
                  </span>
                ) : (
                  <span className="text-xs text-muted">nunca configurado</span>
                )}
              </div>
              {metric !== null && (
                <p className="mt-0.5 text-xs text-muted tabular-nums">
                  desde {formatDate(metric.valid_from)}
                </p>
              )}
              <input
                id={`hr-${field.kind}`}
                type="number"
                inputMode="numeric"
                step="1"
                value={values[field.kind]}
                onChange={(e) =>
                  setValues((prev) => ({ ...prev, [field.kind]: e.target.value }))
                }
                className={INPUT_CLASS}
              />
              {errors[field.kind] !== undefined && (
                <p className="mt-1 text-sm text-red-400">{errors[field.kind]}</p>
              )}
              {metric === null && (
                <p className="mt-1 text-xs text-muted">
                  O primeiro sync preenche sozinho — ou digite o valor e salve.
                </p>
              )}
            </div>
          );
        })}
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <button
          type="submit"
          disabled={saving || !hasAnyInput}
          className="rounded-lg bg-accent px-3 py-2 text-sm font-medium text-background disabled:opacity-60"
        >
          {saving ? "Salvando…" : "Salvar valores"}
        </button>
        {generalError !== null && (
          <p className="text-sm text-red-400">{generalError}</p>
        )}
      </div>
    </form>
  );
}
