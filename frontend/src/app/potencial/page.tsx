import PotentialPanel from "@/components/potential/PotentialPanel";

// Painel Potencial (§4.4) — a lista é client-side (fetch em
// /api/potential, padrão do painel Treinos).
export default function PotencialPage() {
  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-6 sm:px-6">
      <h1 className="text-2xl font-semibold tracking-tight">Potencial</h1>
      <PotentialPanel />
    </main>
  );
}
