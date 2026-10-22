"use client";

// Seção 2 "Método e zonas" (feature hr-zones — HRZ-08/09/13/14):
// seletor dos 3 métodos (lthr/fcr/fcmax) com os percentuais
// pré-carregados dos `defaults` do GET; trocar de método prefilla os
// defaults do método escolhido. Os percentuais são editáveis em
// pontos por zona (5 zonas × low/high) — a Z5 é fixa e honesta:
// lthr = aberta (high null), fcr/fcmax = 100 (fecha em 100%, calc.py
// validate_bounds). Salvar → PUT updateHrZones({method, bounds}) — a
// resposta re-renderiza a página (zonas em bpm mudam na hora,
// HRZ-14); igual ao vigente não cria config (idempotente). 422 de
// bounds chega "zona N: motivo" em PT-BR e vira erro inline na zona
// apontada (HRZ-09).

import { useState, type FormEvent } from "react";

import {
  ApiError,
  updateHrZones,
  type HrZoneBound,
  type HrZoneConfig,
  type HrZoneMethod,
  type HrZonesOut,
} from "@/lib/api";

const METHODS: [HrZoneMethod, string][] = [
  ["lthr", "LTHR%"],
  ["fcr", "Reserva cardíaca"],
  ["fcmax", "FC máx%"],
];

const ZONE_COUNT = 5;

const INPUT_CLASS =
  "w-16 rounded-ctl border border-border hover:border-border-hover bg-card px-2 py-1.5 text-sm text-foreground outline-none focus:border-accent/50";

/** Percentuais como strings editáveis — Z5 do lthr guarda "" (aberta). */
type BoundFields = { low: string; high: string };

function toFields(zones: HrZoneBound[]): BoundFields[] {
  return zones.map((zone) => ({
    low: zone.low.toString(),
    high: zone.high === null ? "" : zone.high.toString(),
  }));
}

/** Inteiro em pontos % — null quando vazio ou não inteiro. */
function parsePercent(raw: string): number | null {
  const trimmed = raw.trim();
  if (trimmed === "") return null;
  const parsed = Number(trimmed);
  return Number.isInteger(parsed) ? parsed : null;
}

export default function HrMethodCard({
  config,
  defaults,
  onSaved,
}: {
  config: HrZoneConfig | null;
  defaults: HrZonesOut["defaults"];
  onSaved: (out: HrZonesOut) => void;
}) {
  const [method, setMethod] = useState<HrZoneMethod>(config?.method ?? "lthr");
  const [fields, setFields] = useState<BoundFields[]>(() =>
    toFields(config?.bounds.zones ?? defaults.lthr),
  );
  const [zoneErrors, setZoneErrors] = useState<(string | undefined)[]>(
    Array(ZONE_COUNT).fill(undefined),
  );
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Trocar de método prefilla os percentuais com os defaults do
  // método (HRZ-08) — os bounds são próprios de cada método.
  function selectMethod(next: HrZoneMethod) {
    if (next === method) return;
    setMethod(next);
    setFields(toFields(defaults[next]));
    setZoneErrors(Array(ZONE_COUNT).fill(undefined));
    setGeneralError(null);
  }

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setGeneralError(null);
    const zones: HrZoneBound[] = [];
    const nextErrors: (string | undefined)[] = Array(ZONE_COUNT).fill(undefined);
    for (let i = 0; i < ZONE_COUNT; i++) {
      const low = parsePercent(fields[i].low);
      const isZ5 = i === ZONE_COUNT - 1;
      // Z5 é fixa (guardrails do backend): lthr aberta, resto 100%
      const high = isZ5
        ? method === "lthr"
          ? null
          : 100
        : parsePercent(fields[i].high);
      if (low === null || (!isZ5 && high === null)) {
        nextErrors[i] = "informe números inteiros";
        continue;
      }
      zones.push({ low, high });
    }
    setZoneErrors(nextErrors);
    if (nextErrors.some((error) => error !== undefined)) return;
    setSaving(true);
    try {
      const out = await updateHrZones({ method, bounds: { zones } });
      onSaved(out);
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) {
        // "zona N: motivo" → inline na zona apontada (HRZ-09)
        const match = /^zona (\d+): (.+)$/.exec(err.message);
        if (match !== null) {
          const idx = Number(match[1]) - 1;
          if (idx >= 0 && idx < ZONE_COUNT) {
            const errs = Array(ZONE_COUNT).fill(undefined);
            errs[idx] = match[2];
            setZoneErrors(errs);
            return;
          }
        }
        setGeneralError(err.message);
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
    <form onSubmit={handleSave} className="space-y-3">
      <div
        role="group"
        aria-label="Método de cálculo"
        className="flex flex-wrap items-center gap-2"
      >
        {METHODS.map(([value, label]) => (
          <button
            key={value}
            type="button"
            aria-pressed={method === value}
            onClick={() => selectMethod(value)}
            className={
              method === value
                ? "rounded-full bg-accent/15 px-3 py-1 text-sm font-medium text-accent"
                : "rounded-full px-3 py-1 text-sm text-muted hover:text-foreground"
            }
          >
            {label}
          </button>
        ))}
        {config !== null && (
          <span className="text-xs text-muted">
            configurado desde{" "}
            {config.valid_from.split("-").reverse().join("/")}
          </span>
        )}
      </div>
      <p className="text-xs text-muted">
        Percentuais por zona em pontos (ex.: 65–80). A Z5 é fixa: aberta no
        LTHR% (sem teto), 100% nos outros métodos.
      </p>
      <div className="space-y-2">
        {fields.map((field, i) => (
          <div key={i}>
            <div className="flex items-center gap-2">
              <span className="w-7 shrink-0 text-sm text-muted tabular-nums">
                Z{i + 1}
              </span>
              <input
                type="number"
                inputMode="numeric"
                step="1"
                aria-label={`Zona ${i + 1} low`}
                value={field.low}
                onChange={(e) =>
                  setFields((prev) => {
                    const next = [...prev];
                    next[i] = { ...prev[i], low: e.target.value };
                    return next;
                  })
                }
                className={INPUT_CLASS}
              />
              <span className="text-sm text-muted">–</span>
              {i === ZONE_COUNT - 1 ? (
                <span className="px-2 text-sm text-muted">
                  {method === "lthr" ? "aberta" : "100"}
                </span>
              ) : (
                <input
                  type="number"
                  inputMode="numeric"
                  step="1"
                  aria-label={`Zona ${i + 1} high`}
                  value={field.high}
                  onChange={(e) =>
                    setFields((prev) => {
                      const next = [...prev];
                      next[i] = { ...prev[i], high: e.target.value };
                      return next;
                    })
                  }
                  className={INPUT_CLASS}
                />
              )}
            </div>
            {zoneErrors[i] !== undefined && (
              <p className="mt-1 text-sm text-red-400">{zoneErrors[i]}</p>
            )}
          </div>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="submit"
          disabled={saving}
          className="rounded-ctl bg-accent px-3 py-2 text-sm font-medium text-background disabled:opacity-60"
        >
          {saving ? "Salvando…" : "Salvar método e zonas"}
        </button>
        {generalError !== null && (
          <p className="text-sm text-red-400">{generalError}</p>
        )}
      </div>
    </form>
  );
}
