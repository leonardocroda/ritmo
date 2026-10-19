"use client";

// Tela de registro por convite (feature auth): nome, email, senha e
// código de convite → POST /api/auth/register via helper `register`
// (T9). Sucesso = 201 + cookie (auto-login, AUTH-01) → entra direto
// nos painéis. Erros exibidos inline: 422 por campo (AuthError.
// fieldErrors — mapa loc→msg do FastAPI) e 403/409 como mensagem única
// no form (design: "inline no form de registro"). 429 não ocorre aqui
// (sem limiter no registro).
//
// Mesmo padrão da tela de login: useSearchParams (next) suspende no
// prerender com cacheComponents — boundary Suspense interna.

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";

import { AuthError, register } from "@/lib/api";

const INPUT_CLASS =
  "mt-1 w-full rounded-lg border border-white/10 bg-card px-3 py-2 text-sm text-foreground outline-none focus:border-accent/50";

function FieldError({ message }: { message: string | undefined }) {
  if (message === undefined) return null;
  return <p className="mt-1 text-sm text-red-400">{message}</p>;
}

function RegisterForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next");
  const [formError, setFormError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    setFieldErrors({});
    setPending(true);
    const data = new FormData(event.currentTarget);
    try {
      await register({
        display_name: String(data.get("display_name") ?? ""),
        email: String(data.get("email") ?? ""),
        password: String(data.get("password") ?? ""),
        invite_code: String(data.get("invite_code") ?? ""),
      });
      // 201 já veio com cookie de sessão (auto-login): entra direto.
      router.replace(next ?? "/treinos");
    } catch (err) {
      if (err instanceof AuthError) {
        setFieldErrors(err.fieldErrors);
        // 403 (convite desabilitado/código inválido) e 409 (email já
        // cadastrado) não mapeiam para um campo — mensagem no topo.
        if (Object.keys(err.fieldErrors).length === 0) {
          setFormError(err.message);
        }
      } else {
        setFormError(
          "Não foi possível criar a conta. Confira o backend e tente de novo.",
        );
      }
      setPending(false);
    }
  }

  return (
    <div className="w-full max-w-xs">
      <p className="text-lg font-semibold tracking-tight">
        Ritmo<span className="text-accent">.</span>
      </p>
      <h1 className="mt-2 text-xl font-semibold">Criar conta</h1>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <div>
          <label htmlFor="display_name" className="text-sm text-muted">
            Nome
          </label>
          <input
            id="display_name"
            name="display_name"
            type="text"
            required
            maxLength={120}
            autoComplete="name"
            className={INPUT_CLASS}
          />
          <FieldError message={fieldErrors.display_name} />
        </div>
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
          <FieldError message={fieldErrors.email} />
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
            autoComplete="new-password"
            className={INPUT_CLASS}
          />
          <FieldError message={fieldErrors.password} />
        </div>
        <div>
          <label htmlFor="invite_code" className="text-sm text-muted">
            Código de convite
          </label>
          <input
            id="invite_code"
            name="invite_code"
            type="text"
            autoComplete="off"
            className={INPUT_CLASS}
          />
        </div>

        {formError !== null && (
          <p className="text-sm text-red-400">{formError}</p>
        )}

        <button
          type="submit"
          disabled={pending}
          className="w-full rounded-lg bg-accent px-3 py-2 text-sm font-medium text-background disabled:opacity-60"
        >
          {pending ? "Criando…" : "Criar conta"}
        </button>
      </form>

      <p className="mt-4 text-center text-sm text-muted">
        Já tem conta?{" "}
        <Link
          href={next !== null ? `/login?next=${encodeURIComponent(next)}` : "/login"}
          className="text-accent hover:underline"
        >
          Entrar
        </Link>
      </p>
    </div>
  );
}

export default function RegistrarPage() {
  return (
    <Suspense fallback={null}>
      <RegisterForm />
    </Suspense>
  );
}
