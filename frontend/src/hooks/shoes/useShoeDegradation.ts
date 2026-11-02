"use client";

import { useEffect, useState, useCallback } from "react";
import { getDegradationBFF, type DegradationOut, type DegradationSignal } from "@/lib/api";
import { getSignalInfo, getDirection, getDirectionColor, getDirectionBg } from "@/lib/shoes/signalLabels";

export interface EnrichedSignal extends DegradationSignal {
  label: string;
  tooltip: string;
  higherIsWorse: boolean;
  direction: "piorou" | "melhorou" | "estável";
  directionColor: string;
  directionBg: string;
}

export interface UseShoeDegradationReturn {
  degradation: DegradationOut | null;
  enrichedSignals: EnrichedSignal[];
  loading: boolean;
  error: string | null;
  refetch: (shoeId: number) => Promise<void>;
}

function enrichSignals(signals: DegradationSignal[]): EnrichedSignal[] {
  return signals.map(s => {
    const info = getSignalInfo(s.sinal);
    const direction = getDirection(s.delta, info.higherIsWorse);
    return {
      ...s,
      label: info.label,
      tooltip: info.tooltip,
      higherIsWorse: info.higherIsWorse,
      direction,
      directionColor: getDirectionColor(direction),
      directionBg: getDirectionBg(direction),
    };
  });
}

export function useShoeDegradation(initialShoeId?: number): UseShoeDegradationReturn {
  const [degradation, setDegradation] = useState<DegradationOut | null>(null);
  const [enrichedSignals, setEnrichedSignals] = useState<EnrichedSignal[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async (shoeId: number) => {
    try {
      setLoading(true);
      setError(null);
      const data = await getDegradationBFF(shoeId);
      setDegradation(data);
      setEnrichedSignals(enrichSignals(data.signals || []));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erro ao carregar degradação";
      setError(message);
      setDegradation(null);
      setEnrichedSignals([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const refetch = useCallback(async (shoeId: number) => {
    await fetchData(shoeId);
  }, [fetchData]);

  // Auto-fetch when shoeId changes
  useEffect(() => {
    if (initialShoeId) {
      fetchData(initialShoeId);
    }
  }, [initialShoeId, fetchData]);

  return { degradation, enrichedSignals, loading, error, refetch };
}