"use client";

// Chip do usuário no header (AUTH-23/24, feature auth): display_name +
// botão "Sair" — única revogação acessível enquanto a /perfil não existe.
// Monta → me(): sucesso renderiza; 401/backend fora não renderiza nada
// (o proxy e a API cuidam do redirect). Sair → logout() revoga a sessão
// CORRENTE no servidor e aterrissa em /login (voltar não reabre o painel).

import { useEffect, useState } from "react";

import { logout, me, type MeOut } from "@/lib/api";

export default function UserMenu() {
  const [user, setUser] = useState<MeOut | null>(null);

  useEffect(() => {
    me()
      .then(setUser)
      .catch(() => {
        // sem sessão (401) ou backend fora: segue sem o chip
      });
  }, []);

  async function handleLogout() {
    try {
      await logout(); // 204 = sessão revogada + cookie limpo
    } catch {
      // sessão já morta/backend fora: o destino é o login de qualquer forma
    }
    // Full reload de propósito (design): derruba o router cache/prefetch
    // da sessão morta — voltar não reabre o painel (UAT do AUTH-24).
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    location.assign("/login");
  }

  if (user === null) return null;

  return (
    <div className="flex items-center gap-2">
      <span className="max-w-20 truncate text-sm text-muted sm:max-w-40">
        {user.display_name}
      </span>
      <button
        type="button"
        onClick={handleLogout}
        className="rounded-full border border-white/10 px-3 py-1.5 text-sm text-muted hover:text-foreground"
      >
        Sair
      </button>
    </div>
  );
}
