// Layout do route group (app): painéis com o Header global (nav +
// sync + conta) e a TabBar inferior no mobile (DSN-17..22). Movido do
// root layout (feature auth) — /login e /registrar ficam no grupo
// (auth), sem header (AUTH-22). URLs não mudam. O wrapper é
// flex-1 flex-col para os <main> das páginas seguirem esticando (body
// é flex-col) e o pb-24 reserva o espaço da tab bar fixa no mobile.
import type { ReactNode } from "react";

import Header from "@/components/Header";
import { TabBar } from "@/components/Nav";

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <Header />
      <div className="flex flex-1 flex-col pb-24 md:pb-0">{children}</div>
      <TabBar />
    </>
  );
}
