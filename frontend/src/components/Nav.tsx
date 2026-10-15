"use client";

// Nav dos 4 painéis (TRN-01/02): Hoje · Treinos · Potencial · Saúde.
// Client component com usePathname para marcar o painel ativo
// (pathname === href ou startsWith(href + "/"), design). Em 390px a
// linha é rolável (overflow-x-auto) em vez de quebrar o header.
//
// usePathname suspende no prerender de rotas com parâmetro dinâmico
// desconhecido quando cacheComponents está ativo (docs Next 16,
// use-pathname.md): a boundary Suspense fica aqui dentro, com fallback
// sem marcação de ativo, para o resto do layout seguir prerenderizável.

import { Suspense } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const PANELS = [
  { href: "/hoje", label: "Hoje" },
  { href: "/treinos", label: "Treinos" },
  { href: "/potencial", label: "Potencial" },
  { href: "/saude", label: "Saúde" },
];

function activePanel(pathname: string): string | null {
  return (
    PANELS.find(
      (panel) => pathname === panel.href || pathname.startsWith(panel.href + "/"),
    )?.href ?? null
  );
}

function NavLinks({ activeHref }: { activeHref: string | null }) {
  return (
    <ul className="flex items-center gap-1">
      {PANELS.map((panel) => {
        const active = panel.href === activeHref;
        return (
          <li key={panel.href}>
            <Link
              href={panel.href}
              aria-current={active ? "page" : undefined}
              className={
                active
                  ? "inline-block whitespace-nowrap rounded-full bg-accent/15 px-3 py-1 text-sm font-medium text-accent"
                  : "inline-block whitespace-nowrap rounded-full px-3 py-1 text-sm text-muted hover:text-foreground"
              }
            >
              {panel.label}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

function ActiveNavLinks() {
  const pathname = usePathname();
  return <NavLinks activeHref={activePanel(pathname)} />;
}

export default function Nav() {
  return (
    <nav className="min-w-0 flex-1 overflow-x-auto" aria-label="Painéis">
      <Suspense fallback={<NavLinks activeHref={null} />}>
        <ActiveNavLinks />
      </Suspense>
    </nav>
  );
}
