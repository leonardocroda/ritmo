// Layout do route group (app): painéis com o Header global (nav +
// sync + conta). Movido do root layout (feature auth) — /login e
// /registrar ficam no grupo (auth), sem header (AUTH-22). URLs não mudam.
import type { ReactNode } from "react";

import Header from "@/components/Header";

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <Header />
      {children}
    </>
  );
}
