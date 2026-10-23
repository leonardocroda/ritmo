"use client";

// Nav — fonte única da navegação (DSN-17..DSN-22): PANELS alimenta as
// duas renderizações CSS-only da mesma verdade — Nav (top bar no
// header, ≥768px) e TabBar (tab bar inferior fixa, <768px). Ícones
// SVG line 22px inline (sem lib nova); item ativo por activePanel
// (pathname === href ou startsWith(href + "/"), com a raiz "/" em
// special-case — ativa só no pathname exato), pill lime/15 na top
// bar e lime/12 na tab bar — continuidade do padrão de pill.
//
// usePathname suspende no prerender de rotas com parâmetro dinâmico
// desconhecido quando cacheComponents está ativo (docs Next 16,
// use-pathname.md): cada renderização que o consome carrega sua
// boundary Suspense aqui dentro, com fallback sem marcação de ativo,
// para o resto do layout seguir prerenderizável.

import { Suspense } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";

function HomeIcon() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M4 11l8-7 8 7v8.5h-5.5V14h-5v5.5H4Z" />
    </svg>
  );
}

function TreinosIcon() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M3 12h4l2.5-6.5 4.5 13 2.5-6.5H21" />
    </svg>
  );
}

function SaudeIcon() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 20.3C7.4 16.7 3.5 13.4 3.5 9.6 3.5 6.9 5.4 5 7.9 5c1.6 0 3.1.8 4.1 2.2C13 5.8 14.5 5 16.1 5c2.5 0 4.4 1.9 4.4 4.6 0 3.8-3.9 7.1-8.5 10.7Z" />
    </svg>
  );
}

function PerformanceIcon() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M3 17l6-6 3.5 3.5L21 6" />
      <path d="M15.5 6H21v5.5" />
    </svg>
  );
}

function PerfilIcon() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="8" r="3.6" />
      <path d="M5 20.2c.9-3.7 3.7-5.5 7-5.5s6.1 1.8 7 5.5" />
    </svg>
  );
}

const PANELS = [
  { href: "/", label: "Home", Icon: HomeIcon },
  { href: "/treinos", label: "Treinos", Icon: TreinosIcon },
  { href: "/saude", label: "Saúde", Icon: SaudeIcon },
  { href: "/performance", label: "Performance", Icon: PerformanceIcon },
  { href: "/perfil", label: "Perfil", Icon: PerfilIcon },
];

function activePanel(pathname: string): string | null {
  // A raiz é special-case (design §Integrações): `startsWith("/")` casaria
  // TODA rota e deixaria a Home sempre ativa — só o pathname exato liga.
  return (
    PANELS.find((panel) =>
      panel.href === "/"
        ? pathname === "/"
        : pathname === panel.href || pathname.startsWith(panel.href + "/"),
    )?.href ?? null
  );
}

function NavLinks({ activeHref }: { activeHref: string | null }) {
  // Na top bar a linha é rolável (overflow-x-auto): o painel ativo
  // pode nascer fora da janela — rolamos o link ativo para dentro da
  // vista (UAT do painel Treinos).
  const activeRef = useRef<HTMLAnchorElement>(null);

  useEffect(() => {
    activeRef.current?.scrollIntoView({ block: "nearest", inline: "center" });
  }, [activeHref]);

  return (
    <ul className="flex items-center gap-1">
      {PANELS.map(({ href, label, Icon }) => {
        const active = href === activeHref;
        return (
          <li key={href}>
            <Link
              ref={active ? activeRef : undefined}
              href={href}
              aria-current={active ? "page" : undefined}
              className={
                active
                  ? "inline-flex items-center gap-1.5 whitespace-nowrap rounded-full bg-accent/15 px-3 py-1 text-sm font-medium text-accent"
                  : "inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-3 py-1 text-sm text-muted hover:text-foreground"
              }
            >
              <Icon />
              {label}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

function TabBarLinks({ activeHref }: { activeHref: string | null }) {
  return (
    <ul className="grid grid-cols-5">
      {PANELS.map(({ href, label, Icon }) => {
        const active = href === activeHref;
        return (
          <li key={href}>
            <Link
              href={href}
              aria-current={active ? "page" : undefined}
              className={
                active
                  ? "flex flex-col items-center gap-0.5 pt-2 text-accent"
                  : "flex flex-col items-center gap-0.5 pt-2 text-muted hover:text-foreground"
              }
            >
              {/* Mesmo size no envoltório dos dois estados: a pill do
                  ativo não muda a altura — os labels ficam alinhados. */}
              <span
                className={
                  active
                    ? "flex size-9 items-center justify-center rounded-full bg-accent/12"
                    : "flex size-9 items-center justify-center"
                }
              >
                <Icon />
              </span>
              <span className="text-[10px] leading-tight">{label}</span>
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

function ActiveTabBarLinks() {
  const pathname = usePathname();
  return <TabBarLinks activeHref={activePanel(pathname)} />;
}

// Top bar do header (≥768px): pills com ícone + label. Abaixo de md a
// top bar some — a navegação mora na TabBar inferior.
export default function Nav() {
  return (
    <nav className="hidden min-w-0 flex-1 overflow-x-auto md:block" aria-label="Painéis">
      <Suspense fallback={<NavLinks activeHref={null} />}>
        <ActiveNavLinks />
      </Suspense>
    </nav>
  );
}

// Tab bar inferior (<768px): fixa, 5 colunas (Home em 1º), alvo de toque
// ≥44px (pt-2 + envoltório size-9 + label) e respiro inferior fixo de
// 18px + safe-area (DSN-22). Some a partir de md.
export function TabBar() {
  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-background/92 pb-[max(18px,env(safe-area-inset-bottom))] backdrop-blur md:hidden"
      aria-label="Painéis"
    >
      <Suspense fallback={<TabBarLinks activeHref={null} />}>
        <ActiveTabBarLinks />
      </Suspense>
    </nav>
  );
}
