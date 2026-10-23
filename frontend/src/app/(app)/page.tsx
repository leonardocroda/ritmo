import HomePanel from "@/components/home/HomePanel";

// Painel Home — a raiz do produto pós-pivot (spec home-panel): o
// veredito do dia no lugar do encaminhamento para /treinos (a AD-016
// do workouts-list é superseded pela AD-025; /hoje segue 404 — nada
// revive a rota deletada). Composição client-side no padrão dos
// demais painéis.
export default function Home() {
  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-6 sm:px-6">
      <h1 className="text-2xl font-semibold tracking-tight">Home</h1>
      <HomePanel />
    </main>
  );
}
