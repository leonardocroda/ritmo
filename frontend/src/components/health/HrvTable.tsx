"use client";

// Tabela diária de HRV (hrv-baseline, HRV-10..12) — noites individuais
// com a média 7d de cada dia, 7 linhas por página (client-side sobre a
// janela carregada, definida pelo filtro de tempo do painel); controles
// Anterior/Próxima e indicador "atual/total" só quando há mais de 7 dias
// com dado.

import { useState } from "react";

import type { HrvBlock } from "@/lib/api";
import { formatVdot } from "@/lib/format";

const PAGE_SIZE = 7;

/** "2026-04-20" -> "20/04/2026" (wall clock, sem conversão de fuso). */
function fullDay(date: string): string {
  const [year, month, day] = date.split("-");
  return `${day}/${month}/${year}`;
}

export default function HrvTable({ hrv }: { hrv: HrvBlock }) {
  const [page, setPage] = useState(0);

  // Só dias com captura, mais recente primeiro (HRV-10)
  const nights = hrv.points
    .filter((p) => p.value !== null)
    .slice()
    .reverse();
  const totalPages = Math.ceil(nights.length / PAGE_SIZE);
  const rows = nights.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  return (
    <div className="mt-4 border-t border-white/10 pt-3">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-left text-[10px] text-muted">
            <th scope="col" className="px-1 py-1.5 font-normal">
              Data
            </th>
            <th scope="col" className="px-1 py-1.5 text-right font-normal">
              HRV
            </th>
            <th scope="col" className="px-1 py-1.5 text-right font-normal">
              Média 7d
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((p) => (
            <tr key={p.date} className="border-t border-white/5">
              <th
                scope="row"
                className="px-1 py-1.5 text-left font-medium whitespace-nowrap"
              >
                {fullDay(p.date)}
              </th>
              <td className="px-1 py-1.5 text-right tabular-nums">
                {p.value !== null ? formatVdot(p.value) : "—"}
              </td>
              <td className="px-1 py-1.5 text-right tabular-nums">
                {p.avg7 !== null ? formatVdot(p.avg7) : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {/* Paginação só com mais de 7 dias com dado (HRV-12) */}
      {totalPages > 1 && (
        <div className="mt-2 flex items-center justify-between text-xs text-muted">
          <button
            type="button"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            className="rounded-full border border-white/10 px-3 py-1 disabled:opacity-40"
          >
            Anterior
          </button>
          <span className="tabular-nums">
            {page + 1}/{totalPages}
          </span>
          <button
            type="button"
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page === totalPages - 1}
            className="rounded-full border border-white/10 px-3 py-1 disabled:opacity-40"
          >
            Próxima
          </button>
        </div>
      )}
    </div>
  );
}
