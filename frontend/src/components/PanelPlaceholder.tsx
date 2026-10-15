// Placeholder dos painéis futuros (TRN-03): nome do painel + "em
// construção" — estrutura pronta para as próximas features da Fase 1.

export default function PanelPlaceholder({ name }: { name: string }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 py-16 text-center">
      <p className="font-mono text-sm text-muted">painel</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight">
        {name}
        <span className="text-accent">.</span>
      </h1>
      <p className="mt-3 text-muted">em construção</p>
    </div>
  );
}
