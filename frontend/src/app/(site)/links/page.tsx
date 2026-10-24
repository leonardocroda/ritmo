// Página de links públicos (feature site) — o "linktree do Ritmo": um
// único endereço para a bio apontar (Instagram aceita um link só).
// Server component estático, zero JS de cliente, identidade v0.3
// (AD-022): dark Night, lime como acento funcional, sentence case.
// A plataforma é o único herói lime da página; GitHub e doc técnica
// em cards neutros.

import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Links — Ritmo",
  description:
    "A plataforma Ritmo, o código no GitHub e a documentação técnica — num só lugar.",
  openGraph: {
    title: "Links — Ritmo",
    description:
      "A plataforma Ritmo, o código no GitHub e a documentação técnica — num só lugar.",
    type: "website",
  },
};

// O pulso — traço derivado da linha de HRV: wordmark (mesmo SVG da
// landing, componente local — nada de JS compartilhado entre rotas).
function Pulse({ className = "h-4 w-5" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 20 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      <path d="M1.5 9h3l2-5.5 3 8.5 2-6 1.5 3h5.5" />
    </svg>
  );
}

// Eyebrow — o único lugar onde caps existe na interface.
function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-accent">
      {children}
    </p>
  );
}

// Card de link — linha do "linktree" na linguagem do site: card com
// borda/raio do app, título + descrição de uma linha, alvo ≥44px.
function LinkCard({
  href,
  title,
  description,
  external = false,
  hero = false,
}: {
  href: string;
  title: string;
  description: string;
  external?: boolean;
  hero?: boolean;
}) {
  const base =
    "group flex min-h-14 items-center justify-between gap-4 rounded-card border px-5 py-4 transition";
  const tone = hero
    ? "border-transparent bg-accent text-on-accent hover:bg-accent/90"
    : "border-border bg-card hover:border-border-hover";
  const body = (
    <>
      <span className="flex flex-col gap-0.5">
        <span className="text-[15px] font-semibold">{title}</span>
        <span
          className={`text-[13px] ${hero ? "text-on-accent/70" : "text-muted"}`}
        >
          {description}
        </span>
      </span>
      <span aria-hidden="true" className="text-lg">
        →
      </span>
    </>
  );
  if (external) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noreferrer"
        className={`${base} ${tone}`}
      >
        {body}
      </a>
    );
  }
  return (
    <Link href={href} className={`${base} ${tone}`}>
      {body}
    </Link>
  );
}

export default function LinksPage() {
  return (
    <main className="mx-auto flex min-h-svh w-full max-w-md flex-col px-5 pb-10 pt-14 sm:pt-20">
      <Link
        href="/"
        className="flex items-center gap-1.5 self-center text-lg font-semibold tracking-tight"
      >
        <Pulse className="h-4 w-5 text-accent" />
        ritmo
      </Link>

      <header className="mt-12 text-center sm:mt-16">
        <Eyebrow>Links</Eyebrow>
        <h1 className="mt-3 text-3xl font-semibold leading-[1.1] tracking-[-0.02em]">
          Tudo do Ritmo,
          <br />
          num <span className="text-accent">só lugar.</span>
        </h1>
        <p className="mt-4 text-[15px] leading-relaxed text-muted">
          A plataforma, o código e a documentação — construídos com IA,
          nos bastidores.
        </p>
      </header>

      <nav
        aria-label="Links do Ritmo"
        className="mt-10 flex flex-col gap-3 sm:mt-12"
      >
        <LinkCard
          href="/"
          hero
          title="A plataforma"
          description="o app — sync do Garmin, painéis e avaliação com IA"
        />
        <LinkCard
          href="https://github.com/leonardocroda/ritmo"
          external
          title="GitHub"
          description="o código aberto do monorepo — backend, frontend e docs"
        />
        <LinkCard
          href="https://ritmo-docs.onrender.com"
          external
          title="Documentação técnica"
          description="API, banco, sync Garmin, frontend e infra — 21 páginas"
        />
      </nav>

      <footer className="mt-auto pt-12 text-center text-xs text-muted">
        plataforma pessoal de corrida · feita com IA, guardrails e
        US$ 0/mês
      </footer>
    </main>
  );
}
