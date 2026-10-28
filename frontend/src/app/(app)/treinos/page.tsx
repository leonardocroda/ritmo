import WorkoutsList from "@/components/workouts/WorkoutsList";
import ShoesSection from "@/components/workouts/ShoesSection";

// Painel Treinos — a home do produto (o "/" redireciona para cá).
// A lista é client-side (fetch em /api/activities, padrão do SyncButton).
export default function TreinosPage() {
  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-6 sm:px-6">
      <h1 className="text-2xl font-semibold tracking-tight">Treinos</h1>
      <WorkoutsList />
      <ShoesSection />
    </main>
  );
}
