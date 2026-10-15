import { notFound } from "next/navigation";
import { Suspense } from "react";

import WorkoutDetail from "@/components/workouts/WorkoutDetail";

// Next 16: params é Promise (version-16.md — acesso síncrono removido).
// Com cacheComponents ativo e sem generateStaticParams, o acesso ao
// parâmetro fica dentro de <Suspense> (dynamic-routes.md, seção
// "Without generateStaticParams").
export default function WorkoutPage(props: PageProps<"/treinos/[id]">) {
  return (
    <Suspense
      fallback={
        <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-6 sm:px-6">
          <p className="text-sm text-muted">Carregando treino…</p>
        </main>
      }
    >
      <WorkoutContent params={props.params} />
    </Suspense>
  );
}

async function WorkoutContent({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  // id numérico validado: não-numérico -> not found (done-when da T11)
  if (!/^\d+$/.test(id)) notFound();
  // key por id: cada treino é uma montagem nova do client component
  return <WorkoutDetail key={id} id={Number(id)} />;
}
