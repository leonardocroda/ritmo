# user-scope Specification

## Problem Statement

Hoje, qualquer sessão autenticada lê e grava sobre o dataset do usuário 1 (`DEFAULT_USER_ID`) — o interim travado até a feature `user-scope` entrar (README §Interim). A Fase 1.5 (AD-012) exige que **todas as queries de leitura e gravação usem o `user_id` do usuário da sessão**, fim do `DEFAULT_USER_ID` em ~30 pontos de consulta, mais um teste de isolamento A×B provando que usuário A não enxerga dados do usuário B. Auth própria já está pronta (feature `auth`, concluída 20/10/2026): `require_session` resolve o cookie para o `User`, e todo router de dado já carrega `dependencies=[Depends(require_session)]`.

## Goals

- [x] Toda query de leitura (activities, saúde, potencial, sync state, avaliações) filtra por `user_id` do usuário autenticado — nunca `DEFAULT_USER_ID`
- [x] Toda gravação (sync de atividades/sono/HRV/etc., criação de avaliação, job de sync) grava com `user_id` do usuário da sessão
- [x] Isolamento A×B: usuário autenticado X não enxerga nem grava sobre dados do usuário Y
- [x] Sem sessão válida → 401 sem dado (proteção já existente, mantida)

## Out of Scope

| Feature | Reason |
| --- | --- |
| Zonas VDOT / LTHR por usuário no banco | Feature 3 da Fase 1.5 (`zones-db`); zonas ainda lêem do `vdot_zones.json` |
| Tokens Garmin no banco (cofre Fernet por usuário) | Feature 4 da Fase 1.5 (`garmin-tokens-db`) |
| `/perfil` (nome, troca de senha, zonas, status Garmin) | Feature 5 da Fase 1.5 (`user-profile`) |
| HTTPS / cookie `Secure` | MVP roda na LAN (AD-012); Fase 2.5 |
| Cadastro via app sem código de convite | Registro desabilitado até `user-scope` estar no ar (assumption do auth) |
| Papéis/admin, cota de IA por usuário | Sem necessidade no MVP; Fase 2.5/3 |
| Delete de conta / exportação LGPD | Fase 2.5 |
| Mudança no frontend (telas, proxy, nav) | Já feito na feature auth; `user-scope` é puramente backend |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| `require_session` já retorna o `User` (feature auth concluída) | Reusar a dependência existente; não criar nova | `require_session` já existe e é aplicada em todos os routers de dado via `main.py` | y |
| Endpoints adicionam `user: User = Depends(require_session)` parâmetro | Cada endpoint de dados passa `user.id` ao service | O `dependencies` de router roda a proteção; o parâmetro expõe o usuário resolvido para o service | y |
| Colunas `user_id` mantêm `default=DEFAULT_USER_ID` nas models | Mantido como rede de segurança; serviços sempre passam `user_id` explicitamente | Evita NOT NULL em paths que ainda não foram migrados; o serviço é a fonte de verdade do isolamento | y |
| conftest: override global de `require_session` (usuário 1) removido | Testes criam sessões por usuário real; novos testes de isolamento | O override global mascarava exatamente o problema que esta feature resolve | y |
| `create_job(db, user_id)` perde o default `DEFAULT_USER_ID` | Parâmetro `user_id` obrigatório | Força o caller (router) a passar o usuário da sessão; nenhum implícito | y |
| Zonas VDOT continuam lendo do arquivo `vdot_zones.json` | Não por usuário ainda | `zones-db` é a próxima feature da Fase 1.5; não entra neste escopo | y |

**Open questions:** none — all resolved or logged above (required before the spec is confirmed).

---

## User Stories

### P1: Leituras de dados por usuário da sessão ⭐ MVP

**User Story**: As a usuário autenticado, I want que cada endpoint de leitura devolva apenas meus próprios dados (atividades, saúde, potencial, sync) so that nenhum outro usuário veja meus treinos e métricas.

**Why P1**: É o núcleo do isolamento multiusuário da Fase 1.5; sem ele, qualquer convidado lê o dataset do usuário 1.

**Acceptance Criteria**:

1. WHEN `GET /api/activities` chega com sessão válida do usuário X THEN o sistema SHALL retornar apenas atividades com `user_id = X`  <!-- event-driven -->
2. WHEN `GET /api/activities/{id}` chega com sessão do usuário X e a atividade tem `user_id = Y ≠ X` THEN o sistema SHALL responder 404 "atividade não encontrada"  <!-- unwanted-behavior -->
3. WHEN `GET /api/health/summary` chega com sessão válida do usuário X THEN o sistema SHALL montar todos os blocos (sono, HRV, RHR, estresse, dose-response, lifestyle) a partir de linhas com `user_id = X`  <!-- event-driven -->
4. WHEN `GET /api/potential` chega com sessão válida do usuário X THEN o sistema SHALL retornar VDOT, predições de prova, PMC e decaimento a partir de linhas com `user_id = X`  <!-- event-driven -->
5. WHEN o estado do sync é consultado com sessão do usuário X (último job e job por id) THEN o sistema SHALL devolver apenas o estado de X — o estado interno por tipo de dado (`sync_state`) é lido e gravado por `user_id` no sync  <!-- event-driven, emendado na validação: a redação original citava um endpoint `sync_state` que nunca existiu como rota HTTP; as superfícies reais são `/api/sync/jobs/latest` e `/api/sync/jobs/{id}` -->
6. WHILE um endpoint de leitura de dados é chamado com sessão válida THEN o sistema SHALL usar o `user_id` do usuário autenticado, nunca `DEFAULT_USER_ID`  <!-- state-driven -->
7. IF uma requisição de leitura de dados chega sem sessão válida THEN o sistema SHALL responder 401 JSON sem nenhum dado  <!-- unwanted-behavior -->

**Independent Test**: logar como usuário X, criar atividade X; logar como usuário Y, criar atividade Y; `GET /api/activities` na sessão de X retorna só a de X; `GET /api/activities/{id_Y}` na sessão de X → 404.

---

### P1: Isolamento A×B ⭐ MVP

**User Story**: As a usuário X, I want que usuário Y não consiga ler, modificar ou ser afetado pelos meus dados so that meus dados permaneçam isolados mesmo compartilhando a mesma instância.

**Why P1**: É a garantia de que o MVP de 5–20 convidados é seguro; é o critério de aceite definitivo da feature.

**Acceptance Criteria**:

1. WHEN usuário X e usuário Y cada um tem atividades, sono, HRV, carga e avaliações no banco THEN `GET /api/activities` na sessão de X SHALL retornar só atividades de X e na sessão de Y SHALL retornar só atividades de Y  <!-- event-driven -->
2. WHEN usuário X tem uma atividade A com avaliação vinculada THEN `GET /api/activities/{A}` na sessão de Y SHALL não listar a avaliação de X (avaliações filtradas por `user_id` da atividade)  <!-- unwanted-behavior -->
3. WHEN `POST /api/sync` é acionado na sessão do usuário X THEN o sistema SHALL criar o `SyncJob` com `user_id = X` e gravar atividades/sono/HRV/etc. com `user_id = X`  <!-- event-driven -->
4. WHEN `POST /api/evaluation` é acionado na sessão do usuário X para a atividade A de X THEN o sistema SHALL gravar a `Evaluation` com `user_id = X`; usuário Y não consegue avaliar a atividade A de X  <!-- event-driven -->
5. IF usuário Y tenta acessar qualquer recurso (atividade, detalhe, avaliação, estado de sync) pertencente a usuário X THEN o sistema SHALL responder 404 ou 401, nunca os dados de X  <!-- unwanted-behavior -->

**Independent Test**: criar usuário X e usuário Y com sessões separadas; cada um insere dados próprios; verificar que X não lê dados de Y em todos os endpoints de leitura e que Y não grava sobre dados de X.

---

### P1: Writes (sync e avaliação) por usuário da sessão ⭐ MVP

**User Story**: As a usuário autenticado, I want que sync e avaliação gravem com o meu `user_id` so that meus dados sincronizados e avaliações fiquem vinculados à minha conta.

**Why P1**: O sync popula o banco com dados do Garmin; se gravar com `DEFAULT_USER_ID`, todos os usuários veriam os dados sincronizados de qualquer um.

**Acceptance Criteria**:

1. WHEN `POST /api/sync` é disparado na sessão do usuário X THEN o sistema SHALL criar o job de sync com `user_id = X` e, ao concluir, gravar cada atividade/sono/HRV/RHR/stress/body_battery/record com `user_id = X`  <!-- event-driven -->
2. WHEN o sync re-puxa os últimos 3 dias + atividades novas para o usuário X THEN o sistema SHALL upsert por chave natural `(user_id, data)` / `(user_id, evento)` / `(activity_id, idx)` de forma isolada por usuário  <!-- event-driven -->
3. WHEN `POST /api/evaluation` é chamado na sessão do usuário X THEN o sistema SHALL gravar `Evaluation.user_id = X` e vincular apenas a atividades com `user_id = X`  <!-- event-driven -->
4. IF o usuário da sessão não tem a atividade A THEN criar avaliação para A SHALL responder 404  <!-- unwanted-behavior -->

**Independent Test**: logar como X, disparar sync (mockado), conferir que `SyncJob.user_id = X` e que atividades gravadas têm `user_id = X`.

---

### P2: Testes de sessão real e isolamento ⭐ MVP

**User Story**: As a desenvolvedor, I want que a suíte de teste exija sessão real por usuário e inclua um teste de isolamento A×B so que regressões de isolamento sejam capturadas automaticamente.

**Why P2**: Sem testes de isolamento, uma mudança futura poderia reintroduzir `DEFAULT_USER_ID` silenciosamente.

**Acceptance Criteria**:

1. WHEN um teste de API de dados roda sem configurar sessão THEN o sistema SHALL responder 401 (o conftest SHALL não injetar automaticamente o usuário 1)  <!-- event-driven -->
2. WHEN um teste cria sessões para usuário X e usuário Y com dados separados THEN o teste de isolamento A×B SHALL passar (X não lê Y, Y não lê X)  <!-- event-driven -->
3. WHILE testes existentes de auth continuam rodando THEN eles SHALL exercer a proteção real (401/cookie/sliding) sem o override global  <!-- state-driven -->

**Independent Test**: `uv run pytest` suíte completa verde, incluindo o novo teste de isolamento A×B; nenhum teste depende do override de usuário 1.

---

## Edge Cases

- IF `GET /api/activities` chega com sessão válida mas o usuário não tem atividades THEN o sistema SHALL retornar lista vazia `[]` com `total = 0` (estado vazio honesto, não erro)
- IF o sync é re-executado para o mesmo usuário THEN o sistema SHALL não criar duplicatas (upsert por chave natural incluindo `user_id`)
- IF duas sessões simultâneas do mesmo usuário disparam sync THEN o sistema SHALL respeitar o lock de um job ativo por usuário (índice parcial existente em `sync_jobs`)
- IF `user_id` é inválido (não existe na tabela `users`) THEN a FK impede o insert (integridade referencial)
- IF um teste cria usuário sem e-mail (seed-like) THEN ele ainda pode ter sessão? Não — sessão requer usuário autenticado via login; testes criam usuário com senha e fazem login

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| USR-01 | P1: Leituras de dados por usuário da sessão | - | ✅ Verified |
| USR-02 | P1: Leituras de dados por usuário da sessão | - | ✅ Verified |
| USR-03 | P1: Leituras de dados por usuário da sessão | - | ✅ Verified |
| USR-04 | P1: Leituras de dados por usuário da sessão | - | ✅ Verified |
| USR-05 | P1: Leituras de dados por usuário da sessão | - | ✅ Verified (texto emendado na validação) |
| USR-06 | P1: Leituras de dados por usuário da sessão | - | ✅ Verified |
| USR-07 | P1: Leituras de dados por usuário da sessão | - | ✅ Verified |
| USR-08 | P1: Isolamento A×B | - | ✅ Verified |
| USR-09 | P1: Isolamento A×B | - | ✅ Verified |
| USR-10 | P1: Isolamento A×B | - | ✅ Verified |
| USR-11 | P1: Isolamento A×B | - | ✅ Verified |
| USR-12 | P1: Isolamento A×B | - | ✅ Verified |
| USR-13 | P1: Writes por usuário da sessão | - | ✅ Verified |
| USR-14 | P1: Writes por usuário da sessão | - | ✅ Verified |
| USR-15 | P1: Writes por usuário da sessão | - | ✅ Verified |
| USR-16 | P1: Writes por usuário da sessão | - | ✅ Verified |
| USR-17 | P2: Testes de sessão real e isolamento | - | ✅ Verified |
| USR-18 | P2: Testes de sessão real e isolamento | - | ✅ Verified |
| USR-19 | P2: Testes de sessão real e isolamento | - | ✅ Verified |

**Coverage:** 19 total, 19 mapped to tasks, 0 unmapped

---

## Success Criteria

- [ ] Toda query de leitura nos serviços (activities, health, potential, evaluation/payload, garmin state) filtra por `user_id` do usuário da sessão — zero ocorrências de `DEFAULT_USER_ID` em queries de domínio (exceto defaults de coluna e seed do usuário 1)
- [ ] Toda gravação (sync, criação de avaliação, job de sync) usa `user_id` do usuário da sessão
- [ ] Teste de isolamento A×B passa: usuário X não lê nem escreve dados do usuário Y em todos os endpoints
- [ ] Suíte completa verde no Postgres do compose (backend) + build do frontend sem erros
- [ ] `curl http://localhost:8000/api/health` continua 200 sem sessão
