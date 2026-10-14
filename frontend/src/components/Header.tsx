// Header global — nome do app + botão "Puxar do Garmin" visível de
// qualquer painel, desktop e mobile (decisão do spec do garmin-sync).
// Server component: só o SyncButton é client (boundary mínimo).

import SyncButton from "@/components/SyncButton";

export default function Header() {
  return (
    <header className="border-b border-white/10">
      <div className="flex items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <span className="text-lg font-semibold tracking-tight">
          Ritmo<span className="text-accent">.</span>
        </span>
        <SyncButton />
      </div>
    </header>
  );
}
