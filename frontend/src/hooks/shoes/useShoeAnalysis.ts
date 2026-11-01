"use client";

import { useEffect, useState, useCallback } from "react";
import { getAnalysisShoes, type AnalysisShoeProfile } from "@/lib/api";
import { compareWorkoutTypes } from "@/lib/shoes/workoutTypeLabels";

export interface UseShoeAnalysisReturn {
  profiles: Map<number, AnalysisShoeProfile>;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useShoeAnalysis(): UseShoeAnalysisReturn {
  const [profiles, setProfiles] = useState<Map<number, AnalysisShoeProfile>>(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getAnalysisShoes();

      // Transform array to Map keyed by shoe_id
      const map = new Map<number, AnalysisShoeProfile>();
      for (const profile of data) {
        // Sort groups by workout type priority
        const sortedGroups = [...profile.groups].sort((a, b) =>
          compareWorkoutTypes(a.tipo, b.tipo)
        );
        map.set(profile.shoe_id, { ...profile, groups: sortedGroups });
      }
      setProfiles(map);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erro ao carregar análise de tênis";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetchData().then(() => {
      if (cancelled) return;
    });
    return () => { cancelled = true; };
  }, [fetchData]);

  const refetch = useCallback(async () => {
    await fetchData();
  }, [fetchData]);

  return { profiles, loading, error, refetch };
}