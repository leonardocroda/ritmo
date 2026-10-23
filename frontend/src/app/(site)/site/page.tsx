// Site público do Ritmo (feature site) — a "capa" da plataforma, morando
// na rota /site (visitante sem sessão a vê na raiz via rewrite do proxy;
// com sessão a raiz segue para os painéis — hoje redirect de
// (app)/page.tsx, Painel Hoje quando a feature dele mergar).
// Identidade visual v0.3 (AD-022): dark Night, lime como acento
// funcional, sentence case, números tabulares, um herói por seção — e
// os prints são da plataforma de verdade (gerados por
// scripts/site/capture.py, sem dado inventado).
//
// Server component estático: zero JS de cliente — só HTML/CSS com as
// fontes e tokens do tema (globals.css). As âncoras usam scroll suave
// (html scroll-behavior, adicionado ao globals).

import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Ritmo — pensar e ver a corrida de um só lugar",
  description:
    "Sync do Garmin, painéis que importam (Treinos · Performance · Saúde) e avaliação de treino com IA sob demanda — com zonas VDOT pessoais e números honestos.",
  openGraph: {
    title: "Ritmo — pensar e ver a corrida de um só lugar",
    description:
      "Sync do Garmin, painéis que importam e avaliação de treino com IA sob demanda.",
    type: "website",
  },
};

/* ------------------------------------------------------------------ */
/* Peças de identidade (v0.3)                                          */
/* ------------------------------------------------------------------ */

// O pulso — traço derivado da linha de HRV: wordmark, divisor, CTA.
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

// Moldura de aparelho (a da demonstração 390px da identidade): o print
// entra na mesma proporção do viewport do capture.py (780×1688 @2x).
function Phone({ src, alt }: { src: string; alt: string }) {
  return (
    <div className="relative z-10 mx-auto w-[300px] sm:w-[340px]">
      <div className="rounded-[48px] border border-border bg-[#05080B] p-[11px] shadow-[0_32px_90px_rgba(0,0,0,0.55)]">
        <div className="overflow-hidden rounded-[38px]">
          {/* eslint-disable-next-line @next/next/no-img-element -- print local, sem otimização de imagem (standalone sem sharp) */}
          <img
            src={src}
            alt={alt}
            width={780}
            height={1688}
            className="block w-full"
          />
        </div>
      </div>
    </div>
  );
}

// Print de elemento "flutuando" — card com a própria borda/raio do app.
function Shot({
  src,
  alt,
  className = "",
}: {
  src: string;
  alt: string;
  className?: string;
}) {
  return (
    <div
      className={`overflow-hidden rounded-card border border-border bg-card shadow-[0_24px_70px_rgba(0,0,0,0.5)] ${className}`}
    >
      {/* eslint-disable-next-line @next/next/no-img-element -- print local, sem otimização de imagem (standalone sem sharp) */}
      <img src={src} alt={alt} loading="lazy" className="block w-full" />
    </div>
  );
}

// Cabeçalho de seção no padrão do documento de identidade: índice
// tabular em lime + título + lead.
function SectionHead({
  idx,
  title,
  lead,
}: {
  idx: string;
  title: string;
  lead: string;
}) {
  return (
    <div className="mx-auto max-w-2xl text-center">
      <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
        <span className="mr-3 text-xs font-bold tracking-[0.1em] text-accent tabular-nums">
          {idx}
        </span>
        {title}
      </h2>
      <p className="mt-3 text-[15px] leading-relaxed text-muted">{lead}</p>
    </div>
  );
}

// Botão que leva à plataforma — lime sólido, alvo ≥44px (identidade).
function CtaButton({
  href,
  children,
  className = "",
}: {
  href: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <Link
      href={href}
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-full bg-accent px-6 py-3 text-[15px] font-semibold text-on-accent transition hover:bg-accent/90 ${className}`}
    >
      {children}
    </Link>
  );
}

// Eyebrow — o único lugar onde caps existe na interface.
function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-accent">
      {children}
    </p>
  );
}

/* ------------------------------------------------------------------ */
/* Seções                                                              */
/* ------------------------------------------------------------------ */

function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/85 backdrop-blur">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-5 py-3 sm:px-8">
        <span className="flex items-center gap-1.5 text-lg font-semibold tracking-tight">
          <Pulse className="h-4 w-5 text-accent" />
          ritmo
        </span>
        <nav className="hidden items-center gap-7 text-sm text-muted md:flex">
          <a href="#como-funciona" className="transition hover:text-foreground">
            Como funciona
          </a>
          <a href="#principios" className="transition hover:text-foreground">
            Princípios
          </a>
        </nav>
        <CtaButton href="/treinos" className="px-5 py-2 text-sm">
          Acessar
        </CtaButton>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section className="relative overflow-hidden px-5 pt-16 sm:pt-24">
      {/* Área lime→transparente (o único gradiente que a identidade
          permite) — luz discretíssima atrás do palco. */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute left-1/2 top-24 h-[380px] w-[680px] -translate-x-1/2 rounded-full bg-accent/[0.06] blur-3xl"
      />
      <div className="relative mx-auto max-w-3xl text-center">
        <Eyebrow>Plataforma pessoal de corrida</Eyebrow>
        <h1 className="mt-4 text-4xl font-semibold leading-[1.05] tracking-[-0.03em] sm:text-6xl">
          Pensar e ver a corrida
          <br />
          de um <span className="text-accent">só lugar.</span>
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-[17px] leading-relaxed text-muted">
          Sync do Garmin, painéis que respondem perguntas de verdade e
          avaliação de treino com IA — quando você pedir. Nada de dashboard
          genérico: cada gráfico existe para responder uma pergunta sua.
        </p>
        <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <CtaButton href="/treinos">
            Ir para a plataforma
            <span aria-hidden="true">→</span>
          </CtaButton>
          <a
            href="#como-funciona"
            className="inline-flex min-h-11 items-center justify-center rounded-full border border-border px-6 py-3 text-[15px] font-medium transition hover:border-border-hover"
          >
            Ver como funciona
          </a>
        </div>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
          {[
            "Sync do Garmin",
            "Zonas VDOT pessoais",
            "IA sob demanda",
            "Números honestos",
          ].map((chip) => (
            <span
              key={chip}
              className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-xs text-muted"
            >
              <span className="size-1.5 rounded-full bg-accent" />
              {chip}
            </span>
          ))}
        </div>
      </div>

      {/* Palco: o app de verdade no meio, os dois heróis flutuando. */}
      <div className="relative mx-auto mt-14 max-w-5xl pb-16 sm:mt-20 sm:pb-24">
        <div className="flex items-center justify-center gap-8">
          <Shot
            src="/prints/splits-chart.png"
            alt="Gráfico de voltas do Ritmo: barras de pace coloridas por zona VDOT com linha de frequência cardíaca"
            className="hidden w-[250px] -rotate-2 self-end lg:block"
          />
          <Phone
            src="/prints/treino-detail.png"
            alt="Detalhe de um treino no Ritmo: métricas, badge de avaliado e contexto do dia"
          />
          <Shot
            src="/prints/evaluation-card.png"
            alt="Card de avaliação com IA: veredito, execução contra intenção e rodapé de auditoria"
            className="hidden w-[250px] rotate-2 self-start pt-10 lg:block"
          />
        </div>
        <p className="mt-10 text-center text-xs text-muted">
          prints reais da plataforma — dados de corrida de verdade
        </p>
      </div>
    </section>
  );
}

function Step({
  n,
  title,
  children,
}: {
  n: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="rounded-card border border-border bg-card p-6">
      <span className="inline-grid size-8 place-items-center rounded-full border border-accent/60 text-sm font-bold text-accent tabular-nums">
        {n}
      </span>
      <h3 className="mt-4 text-lg font-semibold tracking-tight">{title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-muted">{children}</p>
    </div>
  );
}

function HowItWorks() {
  return (
    <section id="como-funciona" className="scroll-mt-20 px-5 py-20 sm:py-24">
      <SectionHead
        idx="01"
        title="Como funciona"
        lead="Do relógio no pulso à análise com IA — em três passos, sem fricção."
      />
      <div className="mx-auto mt-12 grid max-w-5xl gap-4 sm:grid-cols-3">
        <Step n="1" title="Conecte o Garmin">
          Seus tokens ficam cifrados no banco e o primeiro sync puxa{" "}
          <span className="tabular-nums text-foreground">180 dias</span> de
          histórico: atividades, voltas, sono, HRV, carga. Sequencial, com
          backoff — sem derrubar a API.
        </Step>
        <Step n="2" title="Veja o que importa">
          Os painéis leem só o seu banco — rápido e sem rate-limit. Cada um
          responde uma pergunta: como foi esse treino? Qual o meu potencial?
          Meu corpo está absorvendo?
        </Step>
        <Step n="3" title="Peça a análise">
          No detalhe do treino, declare a intenção e peça a avaliação. O
          Python calcula cada número; a IA interpreta e devolve veredito,
          desvios e o que corrigir.
        </Step>
      </div>
    </section>
  );
}

// Feature: eyebrow + pergunta do painel + bullets + prints. `flip`
// alterna o lado do visual entre as seções (ritmo de leitura no
// desktop; no mobile empilha com o visual por último).
function Feature({
  id,
  eyebrow,
  title,
  lead,
  bullets,
  flip = false,
  children,
}: {
  id: string;
  eyebrow: string;
  title: string;
  lead: ReactNode;
  bullets: string[];
  flip?: boolean;
  children: ReactNode;
}) {
  const text = (
    <div className="max-w-xl">
      <Eyebrow>{eyebrow}</Eyebrow>
      <h2 className="mt-3 text-3xl font-semibold leading-tight tracking-[-0.02em]">
        {title}
      </h2>
      <p className="mt-4 text-[15px] leading-relaxed text-muted">{lead}</p>
      <ul className="mt-6 space-y-3">
        {bullets.map((bullet) => (
          <li key={bullet} className="flex gap-3 text-sm leading-relaxed">
            <span className="mt-2 size-1.5 shrink-0 rounded-full bg-accent" />
            {bullet}
          </li>
        ))}
      </ul>
    </div>
  );
  return (
    <section
      id={id}
      className="scroll-mt-20 px-5 py-16 sm:py-20 [&>*]:mx-auto [&>*]:max-w-6xl"
    >
      <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-16">
        {flip ? (
          <>
            {children}
            {text}
          </>
        ) : (
          <>
            {text}
            {children}
          </>
        )}
      </div>
    </section>
  );
}

function Features() {
  return (
    <>
      <div className="mx-auto max-w-6xl px-5">
        <SectionHead
          idx="02"
          title="A plataforma por dentro"
          lead="Prints reais dos painéis — nenhum dado inventado, nenhum mockup."
        />
      </div>

      <Feature
        id="treinos"
        eyebrow="Painel Treinos"
        title="Como foi esse treino, de verdade?"
        lead={
          <>
            O gráfico de voltas conta a história: cada barra colorida pela{" "}
            <span className="text-foreground">zona VDOT pessoal</span> —
            verde fácil, azul maratona, laranja limiar, vermelho intervalado,
            roxo repetição — com largura proporcional à duração e a linha de
            FC por cima. Pausa de 30s não se disfarça de tiro de 3km.
          </>
        }
        bullets={[
          "Splits por zona VDOT sua, com FC e relevo no mesmo gráfico",
          "Consistência: 1ª vs 2ª metade, drift cardíaco, decoupling FC/pace",
          "Contexto do dia: sono, HRV, FC de repouso e temperatura",
          "Tipo inferido (prova, limiar, longão…) e badge de avaliado",
        ]}
      >
        <div className="relative">
          <Phone
            src="/prints/treinos-list.png"
            alt="Lista de treinos no Ritmo: corridas com tipo inferido, pace, FC e badge de avaliado"
          />
          <Shot
            src="/prints/contexto-dia.png"
            alt="Contexto do dia de um treino: chips de sono, HRV, FC de repouso e temperatura"
            className="absolute -bottom-6 left-1/2 w-[220px] -translate-x-1/2 rotate-1 sm:w-[250px] lg:left-auto lg:right-0 lg:translate-x-0"
          />
        </div>
      </Feature>

      <Feature
        id="ia"
        eyebrow="Avaliar com IA"
        title="Execução contra intenção."
        flip
        lead={
          <>
            Você declara a intenção —{" "}
            <span className="text-foreground">
              “era um longão fácil”
            </span>{" "}
            — e pede a análise. O backend monta um payload determinístico
            (zonas por volta, consistência, contexto do dia, PRs) e a IA
            interpreta: veredito, desvios e correções.{" "}
            <span className="text-foreground">
              Zero alucinação de número
            </span>
            : o percentual na zona alvo é sempre o calculado em Python.
          </>
        }
        bullets={[
          "Veredito no alvo, abaixo ou acima — com os desvios nomeados",
          "Zonas VDOT suas + contexto fisiológico do dia na avaliação",
          "Auditoria em cada card: modelo, tokens e data",
          "Sob demanda — nada é avaliado sem você pedir",
        ]}
      >
        <div className="relative">
          <Shot
            src="/prints/evaluation-card.png"
            alt="Card de avaliação com IA no Ritmo: veredito, execução vs intenção, desvios e rodapé com modelo e tokens"
            className="mx-auto w-full max-w-[420px] rotate-1"
          />
        </div>
      </Feature>

      <Feature
        id="performance"
        eyebrow="Painel Performance"
        title="Qual o meu máximo — e a que distância dele estou?"
        lead={
          <>
            A pergunta que nenhum app responde com honestidade. A timeline
            VDOT plota cada prova e teste, a linha do corrente e a{" "}
            <span className="text-foreground">faixa até o demonstrado</span>{" "}
            — a lacuna é o alvo honesto, nunca um número mágico.
          </>
        }
        bullets={[
          "VDOT corrente vs demonstrado, com a lacuna % visível",
          "Previsões por 4 métodos (Garmin, Riegel, VDOT, média honesta) contra PRs",
          "Curva PMC: fitness, fadiga e forma dos últimos 60 dias",
          "Hierarquia clara: provas e testes medem; o relógio só estima",
        ]}
      >
        <div className="relative">
          <Phone
            src="/prints/performance-top.png"
            alt="Painel Performance no Ritmo: linha-guia, seção Onde estou e card da lacuna de VDOT"
          />
          <Shot
            src="/prints/performance-vdot.png"
            alt="Card da lacuna e timeline VDOT: pontos de provas, linha do corrente e faixa sombreada até o demonstrado"
            className="absolute -bottom-4 left-1/2 w-[240px] -translate-x-1/2 -rotate-1 sm:w-[260px] lg:left-auto lg:right-0 lg:translate-x-0"
          />
        </div>
      </Feature>

      <Feature
        id="saude"
        eyebrow="Painel Saúde"
        title="Meu corpo está absorvendo o treino?"
        flip
        lead={
          <>
            O fio: o sono recupera, o corpo responde, dormir mal custa — e a
            vida fora da corrida sustenta tudo. Quatro seções contam essa
            história com os seus dados, incluindo a{" "}
            <span className="text-foreground">dose-resposta pessoal</span>:
            o preço de uma noite curta, visível.
          </>
        }
        bullets={[
          "Sono contra o piso de 7h, fases e REM na banda de 21–31%",
          "HRV noturna com média de 7 dias e banda pessoal de 60 dias",
          "Dose-resposta: noites curtas (<6h) contra adequadas (≥6h45)",
          "Equilíbrio de vida: força, yoga e estresse na janela",
        ]}
      >
        <div className="relative">
          <Phone
            src="/prints/saude-top.png"
            alt="Painel Saúde no Ritmo: seletor de janela, linha-guia e seção de sono"
          />
          <Shot
            src="/prints/dose-response.png"
            alt="Dose-resposta do sono: comparação de HRV e score entre noites curtas e adequadas"
            className="absolute -bottom-6 left-1/2 w-[230px] -translate-x-1/2 rotate-1 sm:w-[250px] lg:left-0 lg:translate-x-0"
          />
        </div>
      </Feature>

      <Feature
        id="zonas"
        eyebrow="Perfil · Zonas de FC"
        title="Zonas com dono, método e histórico."
        lead={
          <>
            FC máxima, FC de repouso e LTHR com fonte (Garmin ou manual) e
            vigência. Escolha o método — LTHR%, reserva cardíaca ou FC máx% —
            e cada mudança vira uma linha datada: treino antigo é lido com as
            zonas da época dele.{" "}
            <span className="text-foreground">
              O passado nunca é reclassificado.
            </span>
          </>
        }
        bullets={[
          "Três métodos de cálculo, percentuais editáveis por zona",
          "Editar manual vence o sync — e registra a preferência",
          "Histórico effective-dated de cada valor e configuração",
        ]}
      >
        <div className="relative">
          <Phone
            src="/prints/perfil-top.png"
            alt="Perfil no Ritmo: conexão Garmin, valores de FC máxima, repouso e LTHR com fonte e vigência"
          />
          <Shot
            src="/prints/hr-zones.png"
            alt="Método e zonas de FC: escolha do método, percentuais e zonas calculadas em bpm"
            className="absolute -bottom-6 left-1/2 w-[220px] -translate-x-1/2 -rotate-1 sm:w-[240px] lg:left-auto lg:right-0 lg:translate-x-0"
          />
        </div>
      </Feature>
    </>
  );
}

function Differentiator() {
  return (
    <section className="px-5 py-16 sm:py-20">
      <div className="mx-auto max-w-3xl rounded-card border-l-[3px] border-accent bg-raised px-6 py-8 sm:px-10">
        <Eyebrow>O que nenhum outro app faz</Eyebrow>
        <p className="mt-4 text-lg leading-relaxed">
          Garmin Connect mostra o que você fez. Strava resume. TrainingPeaks
          planeja. O Ritmo{" "}
          <span className="text-accent">julga como você executou</span>{" "}
          contra o que declarou — com as suas zonas VDOT, o contexto
          fisiológico do dia e os seus padrões. A análise que um coach faria,
          quando você pedir.
        </p>
      </div>
    </section>
  );
}

function Principle({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="rounded-card border border-border bg-card p-6">
      <h3 className="text-base font-semibold tracking-tight">{title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-muted">{children}</p>
    </div>
  );
}

function Principles() {
  return (
    <section id="principios" className="scroll-mt-20 px-5 py-20 sm:py-24">
      <SectionHead
        idx="03"
        title="Por que confiar nos números"
        lead="Decisões de produto que ficam visíveis na interface — não no discurso."
      />
      <div className="mx-auto mt-12 grid max-w-5xl gap-4 sm:grid-cols-2">
        <Principle title="Zero alucinação">
          Todo número é calculado em Python — determinístico e auditável. A
          IA interpreta; nunca inventa métrica.
        </Principle>
        <Principle title="Faixa, nunca número mágico">
          Potencial vem de provas e testes com data. Estimativa do relógio
          aparece com selo de estimativa.
        </Principle>
        <Principle title="Seus dados, seu banco">
          O Garmin só é lido no sync. Os painéis leem o seu Postgres —
          rápido e isolado por usuário.
        </Principle>
        <Principle title="IA sob demanda">
          Avaliação tem custo de tokens e valor de resposta. Nada roda sem
          você pedir — e cada tentativa fica no histórico.
        </Principle>
      </div>
    </section>
  );
}

function FinalCta() {
  return (
    <section className="relative overflow-hidden px-5 py-24 sm:py-32">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute left-1/2 top-1/2 h-[300px] w-[560px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-accent/[0.05] blur-3xl"
      />
      <div className="relative mx-auto max-w-2xl text-center">
        <Pulse className="mx-auto h-8 w-10 text-accent" />
        <h2 className="mt-6 text-3xl font-semibold tracking-[-0.02em] sm:text-4xl">
          Sua corrida, pensada de um só lugar.
        </h2>
        <p className="mx-auto mt-4 max-w-md text-[15px] leading-relaxed text-muted">
          Conecte o Garmin, sincronize e chame a IA quando quiser.
        </p>
        <CtaButton href="/treinos" className="mt-8">
          Ir para a plataforma
          <span aria-hidden="true">→</span>
        </CtaButton>
        <p className="mt-4 text-xs text-muted">
          acesso por convite — peça o código a quem te indicou
        </p>
      </div>
    </section>
  );
}

function SiteFooter() {
  return (
    <footer className="border-t border-border px-5 py-10">
      <div className="mx-auto flex w-full max-w-6xl flex-col items-center justify-between gap-6 text-center sm:flex-row sm:text-left">
        <div>
          <span className="flex items-center justify-center gap-1.5 text-base font-semibold tracking-tight sm:justify-start">
            <Pulse className="h-3.5 w-4 text-accent" />
            ritmo
          </span>
          <p className="mt-2 text-xs text-muted">
            Prints reais da plataforma · dados de corrida de verdade ·
            números honestos
          </p>
        </div>
        <nav className="flex items-center gap-6 text-sm text-muted">
          <Link href="/login" className="transition hover:text-foreground">
            Entrar
          </Link>
          <Link href="/registrar" className="transition hover:text-foreground">
            Criar conta
          </Link>
        </nav>
      </div>
    </footer>
  );
}

export default function SitePage() {
  return (
    <>
      <SiteHeader />
      <main>
        <Hero />
        <HowItWorks />
        <Features />
        <Differentiator />
        <Principles />
        <FinalCta />
      </main>
      <SiteFooter />
    </>
  );
}
