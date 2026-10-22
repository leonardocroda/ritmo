// Header global — wordmark "ritmo" com o pulso de HRV em lime (DSN-25)
// + nav desktop (top bar, ≥768px) + conta (nome + Sair, UserMenu) +
// botão "Puxar do Garmin" visível de qualquer painel, desktop e
// mobile (TRN-01). Server component: só Nav/UserMenu/SyncButton são
// client. Abaixo de md a navegação migra para a TabBar inferior — o
// header fica com wordmark + sync + conta (DSN-21).

import Nav from "@/components/Nav";
import SyncButton from "@/components/SyncButton";
import UserMenu from "@/components/UserMenu";

export default function Header() {
  return (
    <header className="border-b border-border">
      <div className="flex items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <span className="flex shrink-0 items-center gap-1.5 text-lg font-semibold tracking-tight">
          <svg
            width="20"
            height="16"
            viewBox="0 0 20 16"
            fill="none"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
            className="stroke-accent"
          >
            <path d="M1.5 9h3l2-5.5 3 8.5 2-6 1.5 3h5.5" />
          </svg>
          ritmo
        </span>
        <Nav />
        <div className="flex shrink-0 items-center gap-2">
          <UserMenu />
          <SyncButton />
        </div>
      </div>
    </header>
  );
}
