// Header global — nome do app + nav dos painéis + botão "Puxar do
// Garmin" visível de qualquer painel, desktop e mobile (nav do spec
// workouts-list: TRN-01). Server component: só Nav/SyncButton são client.
// A nav vira linha rolável em 390px (overflow dentro do próprio Nav).

import Nav from "@/components/Nav";
import SyncButton from "@/components/SyncButton";

export default function Header() {
  return (
    <header className="border-b border-white/10">
      <div className="flex items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <span className="shrink-0 text-lg font-semibold tracking-tight">
          Ritmo<span className="text-accent">.</span>
        </span>
        <Nav />
        <SyncButton />
      </div>
    </header>
  );
}
