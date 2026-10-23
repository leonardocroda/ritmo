// Header global — wordmark "ritmo" com o pulso de HRV em lime (DSN-25)
// + nav desktop (top bar, ≥768px) + conta (nome + Sair, UserMenu).
// Server component: só Nav/UserMenu são client. Abaixo de md a
// navegação migra para a TabBar inferior — o header fica com wordmark
// + conta (DSN-21, emenda AD-023: o "Puxar do Garmin" vive no /perfil).

import Nav from "@/components/Nav";
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
        </div>
      </div>
    </header>
  );
}
