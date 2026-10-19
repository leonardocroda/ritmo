"use client";

// Tela de login (feature auth): email+senha → POST /api/auth/login via
// helper `login` (T9). Erro do backend exibido inline — a 401 genérica
// ("email ou senha inválidos") e a 429 do lockout já chegam em PT-BR
// no `detail`. Sucesso → router.replace(next ?? "/treinos") (AUTH-18):
// o `next` vem do proxy/wrapper e devolve o usuário à rota original.
//
// useSearchParams suspende no prerender com cacheComponents (mesmo
// padrão do Nav): a boundary Suspense fica aqui dentro.

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";

import { ApiError, login } from "@/lib/api";

const INPUT_CLASS =
  "mt-1 w-full rounded-lg border border-white/10 bg-card px-3 py-2 text-sm text-foreground outline-none focus:border-accent/50";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setPending(true);
    const data = new FormData(event.currentTarget);
    try {
      await login(
        String(data.get("email") ?? ""),
        String(data.get("password") ?? ""),
      );
      // Aterrissa na rota original (AUTH-18); sem next, no painel principal.
      router.replace(next ?? "/treinos");
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Não foi possível entrar. Confira o backend e tente de novo.",
      );
      setPending(false);
    }
  }

  return (
    <div className="w-full max-w-xs">
      <p className="text-lg font-semibold tracking-tight">
        Ritmo<span className="text-accent">.</span>
      </p>
      <h1 className="mt-2 text-xl font-semibold">Entrar</h1>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <div>
          <label htmlFor="email" className="text-sm text-muted">
            Email
          </label>
          <input
            id="email"
            name="email"
            type="email"
            required
            autoComplete="email"
            className={INPUT_CLASS}
          />
        </div>
        <div>
          <label htmlFor="password" className="text-sm text-muted">
            Senha
          </label>
          <input
            id="password"
            name="password"
            type="password"
            required
            autoComplete="current-password"
            className={INPUT_CLASS}
          />
        </div>

        {error !== null && <p className="text-sm text-red-400">{error}</p>}

        <button
          type="submit"
          disabled={pending}
          className="w-full rounded-lg bg-accent px-3 py-2 text-sm font-medium text-background disabled:opacity-60"
        >
          {pending ? "Entrando…" : "Entrar"}
        </button>
      </form>

      <p className="mt-4 text-center text-sm text-muted">
        Não tem conta?{" "}
        <Link
          href={next !== null ? `/registrar?next=${encodeURIComponent(next)}` : "/registrar"}
          className="text-accent hover:underline"
        >
          Criar conta
        </Link>
      </p>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
