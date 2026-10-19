// Layout do route group (auth): mínimo, sem Header/Nav/SyncButton
// (AUTH-22) — as telas de auth não expõem a navegação dos painéis.
import type { ReactNode } from "react";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center px-4">
      {children}
    </main>
  );
}
