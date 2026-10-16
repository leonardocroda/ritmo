import HealthPanel from "@/components/health/HealthPanel";

// Painel Saúde (§4.5) — a composição é client-side (fetch em
// /api/health/summary, padrão do painel Potencial).
export default function SaudePage() {
  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-6 sm:px-6">
      <h1 className="text-2xl font-semibold tracking-tight">Saúde</h1>
      <HealthPanel />
    </main>
  );
}
