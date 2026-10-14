const panels = [
  { name: "Hoje", desc: "readiness · countdown da prova · semana" },
  { name: "Treinos", desc: "splits por zona VDOT + FC + relevo" },
  { name: "Potencial", desc: "timeline VDOT · previsões vs PRs · PMC" },
  { name: "Saúde", desc: "sono · REM · HRV · dose-resposta" },
];

const actions = ["Puxar do Garmin", "Avaliar com IA"];

export default function Home() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 py-16">
      <main className="w-full max-w-md">
        <header className="mb-10 text-center sm:text-left">
          <p className="font-mono text-sm text-muted">fase 0 · esqueleto no ar</p>
          <h1 className="mt-2 text-4xl font-semibold tracking-tight">
            Ritmo<span className="text-accent">.</span>
          </h1>
          <p className="mt-3 text-lg leading-8 text-muted">
            Sua corrida em um só lugar: sync do Garmin, painéis que importam e
            avaliação de treino com IA.
          </p>
        </header>

        <section className="rounded-2xl border border-white/10 bg-card p-6">
          <h2 className="text-sm font-medium text-muted">
            Fase 1 — vem aí (uma feature, um spec)
          </h2>
          <ul className="mt-4 space-y-3">
            {panels.map((panel) => (
              <li key={panel.name} className="flex items-baseline justify-between gap-4">
                <span className="font-medium">{panel.name}</span>
                <span className="text-right text-sm text-muted">{panel.desc}</span>
              </li>
            ))}
          </ul>

          <div className="mt-6 flex flex-wrap gap-2">
            {actions.map((action) => (
              <span
                key={action}
                className="rounded-full border border-accent/30 px-3 py-1 text-sm text-accent opacity-70"
              >
                {action}
              </span>
            ))}
          </div>
        </section>

        <p className="mt-6 text-center text-xs text-muted">
          Cada feature nasce de um spec validado (tlc-spec-driven) · Plano:{" "}
          <code className="font-mono">docs/PLANO_PLATAFORMA.md</code>
        </p>
      </main>
    </div>
  );
}
