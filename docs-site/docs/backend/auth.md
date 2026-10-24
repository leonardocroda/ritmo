# Backend — Auth & Sessões

Auth próprio self-hosted (AD-013): **argon2id + sessão stateful em banco
+ cookie HttpOnly**. Sem dependência externa, revogação trivial, funciona
offline na LAN. O desenho da sessão é a AD-018: **API autoritativa,
proxy otimista** — o FastAPI é quem decide; o Next só olha a presença do
cookie para UX.

## Senhas

- Hash **argon2id** via `argon2-cffi` (`app/auth/security.py`), formato
  PHC em `users.password_hash` — sem política de complexidade na v1
  (pendência conhecida).
- Login compara com hash; erro é **único e genérico** (`401`) — nunca
  revela se falhou o email ou a senha.

## Sessão (stateful, AD-018)

| Peça | Valor |
|---|---|
| Token | opaco, `secrets.token_urlsafe(32)` — vai no cookie |
| Banco | `sessions.token_hash` = **SHA-256 do token** (o valor cru nunca é persistido) |
| Cookie | `ritmo_session` · `HttpOnly` · `SameSite=Lax` · **host-only** (sem `Domain`) · `Max-Age` = 30d |
| `Secure` | `SESSION_COOKIE_SECURE` — `false` local (HTTP LAN), `true` em produção |
| Sliding | request autenticado com ≤15d restantes (`SESSION_RENEW_THRESHOLD_DAYS`) → `expires_at = now + 30d` + cookie re-set — usuário ativo nunca cai no meio |
| Logout | DELETE da sessão do banco + cookie removido — **só o dispositivo atual** |
| JWT | avaliado e descartado: revogação exigiria denylist; o lookup no Postgres custa <1ms |

Login com sucesso faz prune lazy das sessões expiradas do usuário.

## Registro por convite

- `POST /api/auth/register` exige `INVITE_CODE` — comparação
  **constant-time** (`hmac.compare_digest`).
- **Código vazio no env = registro desabilitado** (`403`) — o acesso por
  convidado abre só quando o operador quiser.
- Email normalizado (trim + lowercase) e único (`409`).
- Cadastro válido responde `201` **já logado** (auto-login + cookie).

## Rate limit

Em memória (`app/auth/rate_limit.py`): **5 falhas por email em 15 min →
`429`** mesmo com a senha correta depois. Sem persistência — restart
limpa (aceitável para o perfil de ameaça atual).

## Proteção de rotas

`require_session` (`app/auth/deps.py`) resolve o cookie → hash → sessão
válida → injeta o `user_id`; aplicada **por include de router** no
`main.py` (7 routers de dados), ficando públicos apenas `/api/health`,
`/api/auth/register` e `/api/auth/login`. O `401` é o contrato — o
client redireciona para `/login?next=<rota atual>`.

Três camadas, uma autoridade:

```text
proxy.ts (Next)      presença do cookie → redirect de UX (nunca valida)
apiFetch (client)    401 em uso → /login?next=
require_session      valida token no banco — A DECISÃO
```

## CLI de bootstrap/suporte

```bash
cd backend
uv run python -m app.auth.set_password   # email via input, senha via getpass
```

- Vincula email+senha ao **usuário seed id 1** (preserva o display_name).
- Conta existente: troca o hash (reset de suporte) sem tocar o nome.
- Email desconhecido: cria conta nova.

## Isolamento por usuário (user-scope)

Toda query de leitura e gravação usa o `user_id` da sessão — painéis,
sync e avaliações são isolados por dono, testado ponta a ponta na suíte
(`tests/test_user_isolation.py`, cenário A×B). O `404` de recurso
alheio não revela existência.
