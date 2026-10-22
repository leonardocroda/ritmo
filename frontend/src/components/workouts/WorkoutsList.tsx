"use client";

// Lista de treinos (TRN-04/05/08/10/11/12): filtro corridas/todas,
// paginação "Carregar mais" anexando sem duplicatas, badge "Avaliado",
// estados vazio/erro. Padrão de fetch/estado do SyncButton: client
// component com estado local, leitura só do banco via /api/activities.

import { useEffect, useRef, useState } from "react";
import Link from "next/link";

import {
  getActivities,
  type ActivityListItem,
  type ActivityTypeFilter,
} from "@/lib/api";
import {
  formatDateTime,
  formatDuration,
  formatInferredType,
  formatKm,
  formatPace,
} from "@/lib/format";

const PAGE_SIZE = 30;

const FILTERS: { value: ActivityTypeFilter; label: string }[] = [
  { value: "running", label: "Corridas" },
  { value: "all", label: "Todas" },
];

function messageOf(err: unknown): string {
  return err instanceof Error ? err.message : "Erro inesperado";
}

function Item({ item }: { item: ActivityListItem }) {
  return (
    <li>
      <Link
        href={`/treinos/${item.id}`}
        className="flex items-center justify-between gap-3 rounded-card border border-border bg-card px-4 py-3 hover:border-accent/40"
      >
        <div className="min-w-0 flex-1">
          <p className="flex items-center gap-2">
            <span className="truncate font-medium">
              {item.name ?? "Sem nome"}
            </span>
            {item.evaluated && (
              <span className="shrink-0 rounded-full bg-accent/15 px-2 py-0.5 text-xs font-medium text-accent">
                Avaliado
              </span>
            )}
          </p>
          <p className="mt-0.5 text-sm text-muted">
            {formatDateTime(item.start_time)}
            {item.inferred_type !== null &&
              ` · ${formatInferredType(item.inferred_type)}`}
            {item.distance_m > 0 && ` · ${formatKm(item.distance_m)}`}
          </p>
        </div>
        <div className="shrink-0 text-right text-sm tabular-nums">
          <p>
            {item.pace_s !== null
              ? `${formatPace(item.pace_s)}/km`
              : formatDuration(item.duration_s)}
          </p>
          {item.avg_hr !== null && (
            <p className="text-muted">{item.avg_hr} bpm</p>
          )}
        </div>
      </Link>
    </li>
  );
}

export default function WorkoutsList() {
  const [filter, setFilter] = useState<ActivityTypeFilter>("running");
  const [items, setItems] = useState<ActivityListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestSeq = useRef(0);

  // Troca de filtro reseta a paginação (done-when): o reset acontece no
  // handler e o effect abaixo só busca a página nova (sem setState
  // síncrono em effect — regra react-hooks/set-state-in-effect).
  function changeFilter(value: ActivityTypeFilter) {
    if (value === filter) return;
    setFilter(value);
    setItems([]);
    setTotal(0);
    setOffset(0);
    setLoading(true);
    setError(null);
  }

  // O seq descarta a resposta velha quando o filtro muda no meio do fetch.
  useEffect(() => {
    const seq = ++requestSeq.current;
    getActivities({ activityType: filter, limit: PAGE_SIZE, offset: 0 })
      .then((data) => {
        if (seq !== requestSeq.current) return;
        setItems(data.items);
        setTotal(data.total);
        setOffset(data.items.length);
      })
      .catch((err: unknown) => {
        if (seq !== requestSeq.current) return;
        setError(messageOf(err));
      })
      .finally(() => {
        if (seq === requestSeq.current) setLoading(false);
      });
  }, [filter]);

  async function loadMore() {
    const seq = ++requestSeq.current;
    setLoadingMore(true);
    setError(null);
    try {
      const data = await getActivities({
        activityType: filter,
        limit: PAGE_SIZE,
        offset,
      });
      if (seq !== requestSeq.current) return;
      setOffset(data.offset + data.items.length);
      // Anexa sem duplicatas: um re-sync entre cliques pode repetir um id
      setItems((prev) => {
        const seen = new Set(prev.map((item) => item.id));
        return [...prev, ...data.items.filter((item) => !seen.has(item.id))];
      });
      setTotal(data.total);
    } catch (err: unknown) {
      if (seq === requestSeq.current) setError(messageOf(err));
    } finally {
      if (seq === requestSeq.current) setLoadingMore(false);
    }
  }

  const hasMore = offset < total;

  return (
    <div className="mt-4">
      <div className="flex items-center gap-2" role="group" aria-label="Filtro de atividades">
        {FILTERS.map((option) => {
          const active = option.value === filter;
          return (
            <button
              key={option.value}
              type="button"
              aria-pressed={active}
              onClick={() => changeFilter(option.value)}
              className={
                active
                  ? "rounded-full bg-accent/15 px-3 py-1 text-sm font-medium text-accent"
                  : "rounded-full px-3 py-1 text-sm text-muted hover:text-foreground"
              }
            >
              {option.label}
            </button>
          );
        })}
      </div>

      {loading && <p className="mt-6 text-sm text-muted">Carregando treinos…</p>}

      {!loading && error !== null && (
        <p className="mt-6 rounded-card border border-border bg-card px-4 py-3 text-sm text-muted">
          Não foi possível carregar os treinos: {error}
        </p>
      )}

      {!loading && error === null && total === 0 && (
        <p className="mt-6 rounded-card border border-border bg-card px-4 py-6 text-sm text-muted">
          Nenhuma atividade por aqui. Use o botão &ldquo;Puxar do Garmin&rdquo; no topo
          para sincronizar seus dados.
        </p>
      )}

      {!loading && items.length > 0 && (
        <ul className="mt-4 space-y-2">
          {items.map((item) => (
            <Item key={item.id} item={item} />
          ))}
        </ul>
      )}

      {hasMore && !loading && (
        <div className="mt-4 flex justify-center">
          <button
            type="button"
            onClick={loadMore}
            disabled={loadingMore}
            className={
              loadingMore
                ? "rounded-full border border-border bg-card px-4 py-1.5 text-sm font-medium text-muted"
                : "rounded-full border border-accent/30 px-4 py-1.5 text-sm font-medium text-accent hover:bg-accent/10"
            }
          >
            {loadingMore ? "Carregando…" : "Carregar mais"}
          </button>
        </div>
      )}
    </div>
  );
}
