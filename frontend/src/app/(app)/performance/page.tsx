import PerformancePanel from "@/components/performance/PerformancePanel";

// Painel Performance (ex-Potencial §4.4 — AD-017) — a lista é client-side
// (fetch em /api/potential, padrão do painel Treinos).
export default function PerformancePage() {
  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-6 sm:px-6">
      <h1 className="text-2xl font-semibold tracking-tight">Performance</h1>
      <PerformancePanel />
    </main>
  );
}
