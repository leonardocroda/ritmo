# Auditoria de Erros — Refactor Backend Decoupling

**Data:** 02/11/2026
**Status da Fase 1 (restaurar plataforma): ✅ CONCLUÍDA** — todos os ERR-01..16 e HER-01..04
endereçados; frontend `tsc` limpo; plataforma testada manualmente de ponta a ponta.
Observação de processo: as duas primeiras suítes completas pós-fix foram invalidadas por
contaminação (duas sessões pytest concorrentes no mesmo `ritmo_test` — IntegrityError em
massa); a suíte de confirmação limpa roda em background após o merge. O squash-merge na
main existe exatamente para tornar qualquer retrabalho um único `git revert`.
**Branch:** `refactor/backend-decoupling` @ `452b1e0`
**Baseline de comparação:** `main` @ `a3e89a5` (worktree temporário em `%TEMP%\opencode\ritmo-main` — remover com `git worktree remove` quando não for mais necessário)
**Método:** diff completo `main...HEAD`, inspeção de contratos frontend↔backend (cada função de `frontend/src/lib/api.ts` vs. routers reais), suíte pytest na branch e na main (baseline), `tsc --noEmit` no frontend, leitura linha a linha dos services/adapters novos.

---

## ⚠️ Contexto crítico: a main já está vermelha

A suíte de testes **já falha na `main`** (60 testes de API legada) desde o commit `a3e89a5`
("VDOT recalibration API + database as single source of truth"), que migrou as zonas de
arquivo para o banco **sem atualizar os testes/seed**. A branch herdou essas falhas e
acrescentou 1 nova (`test_garmin_tokens_store`). **Não trate as falhas herdadas como
regressão deste refactor** — mas elas precisam entrar no plano, porque o objetivo é
"todas as funcionalidades funcionando".

| Suíte | Resultado |
|---|---|
| Branch (completa) | **61 failed / 823 passed** + 1 collection error (`test_vdot_calibration.py`, herdado) |
| Main (mesmo subset) | **60 failed / 108 passed** — mesmíssima lista, exceto `test_garmin_tokens_store` (nova na branch) |
| Frontend `tsc --noEmit` | ✅ limpo (compila sem erros) |

---

## Mapa de funcionalidades × estado (visão do usuário)

| Funcionalidade | Estado | Erros |
|---|---|---|
| Home (hoje) | ✅ OK (BFF → service legado) | — |
| Sync Garmin (iniciar/poll) | ⚠️ Funciona, mas 2º clique (job ativo) → **500 em vez de 409** | ERR-13 |
| Conexão Garmin (perfil) | ✅ OK | — |
| Painel Saúde | ✅ OK (BFF → service legado) | — |
| Painel Performance | ✅ OK (BFF → service legado) | — |
| Treinos — lista | ⚠️ Carrega, mas **badge de tipo errado** (tudo "Fácil"/"Longo") | ERR-09 |
| Treinos — detalhe | ⚠️ Zonas do gráfico **todas verdes "Easy"**, legenda "—", **km_label vazio**, bloco de contexto some, histórico de avaliações some | ERR-08, ERR-10, ERR-07, ERR-06 |
| Avaliar com IA | ❌ **QUEBRADO** — 404 no POST e no polling | ERR-01 |
| Zonas FC (leitura) | ⚠️ Métricas/config OK, mas **zonas derivadas nunca vêm** (null) | ERR-11 |
| Zonas FC (edição) | ❌ **QUEBRADO** — PUT responde 200 mas **não salva nada** | ERR-11 |
| Zonas de Ritmo (VDOT) | ❌ **QUEBRADO** — shape errado derruba a página; recalibrar funciona (endpoint antigo) mas a página não renderiza | ERR-04 |
| Equipamentos — lista/CRUD | ⚠️ Persiste, mas **km atual, corridas, vida útil: tudo 0/null** | ERR-12 |
| Equipamentos — associação a treino | ✅ OK (endpoint antigo mantido) | — |
| Degradação de tênis | ❌ **QUEBRADO nos 2 caminhos** (404 na rota antiga; stub vazio na BFF) | ERR-03, ERR-12 |
| Análise comparativa de tênis | ❌ **QUEBRADO** — 404 | ERR-02 |

---

## Regressões introduzidas pela branch

### A. Rotas — frontend chama endpoints que não existem (404)

#### ERR-01 · Avaliar com IA: 404 no POST e no polling — 🔴 crítico
- **Sintoma:** clicar em "Avaliar com IA" dá 404; polling de avaliação dá 404.
- **Causa:** `frontend/src/lib/api.ts` migrou para `POST /api/v1/activities/{id}/evaluate` e
  `GET /api/v1/activities/{id}/evaluate/{evaluationId}`, mas esses endpoints **não existem** —
  o único router com evaluate é o legado `app/evaluation/router.py` (`/api/activities/...`).
  O router de domínio `app/domain/activity/router.py` só tem list + detail.
- **Arquivos:** `frontend/src/lib/api.ts` (evaluateActivity, getEvaluation), `backend/app/evaluation/router.py`.
- **Correção sugerida:** expor as rotas em `/api/v1/activities/{id}/evaluate[/{evalId}]`
  (router de domínio ou BFF) **delegando ao `app/evaluation/router.py`-level service**
  (mesmo padrão do BFF Home/Health/Performance), ou reverter o frontend ao path legado.

#### ERR-02 · Análise comparativa de tênis: 404 — 🔴 crítico
- **Sintoma:** página de análise/comparação de tênis sem dados (404).
- **Causa:** frontend chama `/api/v1/tenis/analysis/shoes[/{id}]` e `/api/v1/tenis/analysis/compare`;
  backend ainda serve **`/api/tenis/analysis/...`** (router legado, prefixo inalterado).
- **Correção sugerida:** idem ERR-01 — nova rota `/api/v1/...` delegando ao service legado
  (`app/tenis_analysis/`), ou reverter frontend.

#### ERR-03 · Degradação de tênis (rota antiga): 404 — 🔴 crítico
- **Sintoma:** aba "Degradação" no detalhe do equipamento sem dados (404).
- **Causa:** frontend chama `/api/v1/tenis/degradation/{id}` (`getDegradation`, usado por
  `useShoeDegradation`); backend serve `/api/tenis/degradation/{id}`. O caminho BFF
  (`/api/v1/bff/shoes/{id}/degradation`) existe, mas responde payload **vazio** (ver ERR-12).
- **Correção sugerida:** unificar num único endpoint funcional (delegar ao service legado
  `app/tenis_degradation/`) e apontar o frontend para ele.

#### ERR-04 · Zonas de Ritmo: shape errado derruba a página — 🔴 crítico
- **Sintoma:** página `/pace-zones` quebra (crash de render) ou mostra lixo; `data.vdot` vira
  objeto, `data.zones`/`data.equivalencias` undefined.
- **Causa:** frontend espera o shape legado `PaceZonesOut` (`vdot: number`, `source`,
  `test_date`, `distancia_metros`, `tempo_segundos`, `zones: Record<chave, PaceZone>`,
  `equivalencias`), mas `GET /api/v1/vdot` retorna `VDOTOut` — que é o shape do **painel
  Performance** (`vdot: {current,...}`, `timeline`, `predictions`, `decay`).
  O `RecalibrateModal` continua no endpoint antigo (`/api/profile/pace-zones/recalibrate`).
- **Arquivos:** `backend/app/domain/vdot/service.py` + `schemas.py`, `frontend/src/app/(app)/pace-zones/page.tsx`.
- **Correção sugerida:** `/api/v1/vdot` deve retornar o contrato de **zonas de ritmo**
  (shape legado). O payload de Performance já existe no BFF `/api/v1/bff/performance`.

#### ERR-05 · `getPotential` aponta para `/api/v1/athlete` — 🟡 latente (dead code)
- `getPotential()` em `api.ts` agora chama `GET /api/v1/athlete`, que retorna `AthleteOut`
  (perfil do atleta) — não `PotentialOut`. Hoje nenhuma tela usa `getPotential` (usam
  `getPerformanceBFF`), mas é uma bomba relógio de contrato. Corrigir ou remover a função.

### B. BFF/domínio — 200 com dado errado, incompleto ou não persistido

#### ERR-06 · Detalhe do treino: `evaluations` sempre `[]` — 🔴 crítico
- `app/domain/activity/service.py` → `get_detail()`: `evaluations=[],  # TODO: buscar avaliações`.
  O histórico de avaliações IA desaparece do detalhe (a UI oculta a seção quando vazia).
- **Correção:** popular via repositório de evaluations (ou delegar ao service legado
  `app/activities/service.py`, que já faz isso).

#### ERR-07 · Detalhe do treino: `context` sempre vazio — 🔴 crítico
- Mesmo arquivo: `_to_context_out()` retorna `ContextOut()` com `# TODO: buscar sono, HRV, RHR`.
  O bloco "Contexto" (sono/HRV/FC repouso/temperatura) desaparece do detalhe.

#### ERR-08 · Classificação de zonas quebrada no pipeline novo — 🔴 crítico
Três defeitos combinados:
1. `classify_splits()` (`domain/services.py`) **copia** `split.zone` sem classificar — e o
   `SQLAlchemySplitRepository._to_domain()` deixa `zone=None` ("será classificada pelo service" — nunca é).
2. `DBZoneConfigProvider._parse_pace_range()` não sabe parsear o formato real do banco
   (`"5:51/km-4:53/km"`): `int("51/km")` → exceção capturada → **todas as faixas viram
   `(None, None)`** → `classify_pace()` devolve sempre a **primeira** zona ("easy").
   Efeito no detalhe: todas as voltas verdes "Easy"; legenda com `pace_range "—"`.
3. O legado classifica por **velocidade (m/s)** com cut points de midpoint (`ZoneConfig.classify`);
   o novo tenta classificar por pace com bandas — algoritmo divergente do design.

#### ERR-09 · `inferred_type` degradado na listagem — 🟠 alto
- `repo.list()` não carrega splits → `classify_splits(())` → vazio → `infer_type` só consegue
  devolver `"facil"` (ou `"longao"` por distância). Além disso `infer_type(None, ...)`
  nunca recebe `raw_json` → **"prova" nunca é inferido**. Badges da lista de treinos errados.

#### ERR-10 · `km_label` vazio no detalhe — 🟠 alto
- `SQLAlchemySplitRepository._to_domain()` seta `km_label=""` ("preenchido pelo service"),
  mas o service (`_to_splits_out`) usa `split.km_label` direto → barras de split sem rótulo.
  (O labeling por distância acumulada só existe no `_to_domain` do **activity** repo, que
  recebe `splits=()`.)

#### ERR-11 · Zonas FC: PUT não salva e zonas derivadas nunca calculadas — 🔴 crítico
- `app/domain/heart_rate_zones/service.py`:
  - `update_hr_zones()` → `# TODO: implementar atualização real` → devolve o estado atual
    **sem persistir**. A tela de Zonas FC "salva" com 200 e perde tudo ao recarregar.
    (Os `save_*` do repo também são placeholders que retornam a entrada.)
  - `get_hr_zones()` retorna `zones=None` **sempre** — as zonas derivadas em bpm (HRZ-10)
    nunca são calculadas (lógica existe no service legado `app/profile/` + `app/profile/calc.py`).
  - `sync_modes` do PUT é ignorado (HRZ-20/21/22).
- **Correção:** delegar ao service legado (`app/profile/router.py` já tem GET/PUT/históricos
  completos) ou implementar de verdade.

#### ERR-12 · Equipamentos: km/corridas/vida útil zerados + degradação stub — 🔴 crítico
- `app/domain/equipment/service.py`:
  - `_to_shoe_out()` → **hardcoded** `current_km=0.0, run_count=0, last_use=None, life_pct=None`
    (a lógica real existe em `app/shoes/service.py` e é alimentada por atividades).
  - `_calculate_attribution_30d_pct()` → sempre `None` (badge TEN-28 some).
  - `get_degradation()` → `total_km=0, n_runs=0` hardcoded; e o repo retorna `None`
    (`get_degradation`/`get_runs` são stubs) → BFF sempre responde "insuficiente".
    A análise real existe em `app/tenis_degradation/` e `app/tenis_analysis/`.
- Efeito: lista de tênis toda zerada; degradação vazia pela BFF; 404 pela rota antiga (ERR-03).

#### ERR-13 · Sync duplicado devolve 500 em vez de 409 — 🟠 alto
- `app/domain/garmin_sync/router.py` (`POST /api/v1/garmin-sync/sync`) não captura
  `JobConflictError` (o legado `app/garmin/router.py` captura → **409** com o job corrente).
  O `SyncButton` espera 409 ("cai no refresh") — com 500 o usuário vê erro de sync.
- Também: parâmetro `window_days` é aceito e **ignorado**.

#### ERR-14 · `main.py`: dependências de auth montadas mas descartadas — 🟠 alto (higiene/risco)
- O novo mecanismo `app.router.routes.extend(router.routes)` **não aplica** os
  `Depends(require_session)` das tuplas — o próprio comentário admite ("dependencies via
  extend doesn't apply Depends"). Hoje não há buraco **por sorte**: todos os routers antigos
  declaram `require_session` inline por endpoint. Mas:
  - o "mapa do que é público" (design auth) virou mentira;
  - qualquer router novo sem dep inline nasce **público** silenciosamente;
  - o comentário "FastAPI 0.162+: include_router doesn't work" é falso.
- **Correção:** voltar para `app.include_router(router, dependencies=[Depends(require_session)])`.

#### ERR-15 · Violação GTDB-13 + stubs de token — 🟠 alto
- `app/domain/garmin_sync/adapters/sqlalchemy_repo.py` acessa `token_encrypted` diretamente e
  ainda devolve o **blob cifrado** como `access_token` ("# Simplificado"). Viola a invariante
  "só `tokens_store` toca a coluna cifrada" — teste novo falhando:
  `tests/test_garmin_tokens_store.py::test_only_tokens_store_touches_the_encrypted_column`.
- `app/domain/garmin_sync/dependencies.py` define **outros** stubs "Placeholder adapters"
  (`SQLAlchemyTokenStore` que sempre devolve `None`, `GarminAPIClient` que devolve listas
  vazias) e injeta no `SyncService` — que os **ignora** (usa `GarminGateway.from_user`).
  Código morto perigoso: se alguém "consertar" o DI, o sync passa a usar o cliente fake.
- **Correção:** apagar os adapters/stubs do domínio garmin_sync e fazer o service delegar ao
  módulo legado (`app/garmin/`) — é o que ele já faz por baixo dos panos.

#### ERR-16 · Arquivos mortos/quebrados e lixo de commit — 🟡 médio
- `app/domain/activity/adapters/sqlalchemy_split.py` importa `app.domain.activities` (**plural —
  o pacote não existe**) → `ModuleNotFoundError` se alguém importar. Hoje ninguém importa
  (o repo real está em `sqlalchemy_repo.py`).
- `app/domain/*/.gitkeep` commitados na **raiz do repo** (fora de `backend/`) — criação de
  diretórios no cwd errado.
- `backend/app/vdot/zones.py`: `import json` duplicado (topo e dentro da função).
- Duplicação de schemas: `app/bff/activities/schemas.py` é cópia colada de
  `app/domain/activity/schemas.py` (o BFF sequer usa as cópias — os services devolvem os
  schemas do domínio).

---

## Problemas herdados da `main` (não são culpa da branch, mas bloqueiam "tudo funcionando")

| ID | Problema | Evidência |
|----|----------|-----------|
| HER-01 | ~60 testes de API legada falham na main desde `a3e89a5` (zonas migradas p/ banco sem atualizar testes/seed): `test_activities_api`, `test_potential_api`, `test_home_*`, `test_pace_zones_api`, `test_tenis_analysis_api`, `test_shoes_api`, `test_user_isolation`, `test_splits_running_dynamics_api`, `test_vdot_daniels` | Baseline rodada no worktree da main: 60 failed |
| HER-02 | `tests/test_vdot_calibration.py` importa `load_calibration`, que não existe (`load_calibration_from_db`) → collection error bloqueia a suíte inteira com `-x` | pytest: ImportError |
| HER-03 | `tests/test_workouts_config.py` testa `Settings.vdot_zones_path`, campo que não existe mais em `app/core/config.py` | AttributeError |
| HER-04 | Contratos de `test_home_api`/`test_home_service`/`test_home_predictions` falham (pré-existentes) | mesma falha nas duas branches |
| HER-05 | A fórmula fechada de `app/vdot/daniels.py` (fonte que gerou a calibração 50.2) diverge das tabelas impressas de Daniels em ~0.2–1.3 VDOT nas distâncias intermediárias (ex.: 5K 19:30 → 51.3 na fórmula vs 50.0 na tabela). Pins de `test_pace_zones_api` re-alinhados à fórmula na Fase 1; decidir em produto se vale trocar por interpolação de tabela Daniels. | pins recalibrate |

---

## Dívida / divergências vs. spec (`.specs/features/backend-decoupling/`)

| ID | Divergência |
|----|-------------|
| DIV-01 | Spec diz `app/screens/` + `/api/v1/screens/*` (DEC-06/DEC-09); código criou `app/bff/` + `/api/v1/bff/*`. Atualizar a spec (recomendado — "bff" descreve melhor) ou renomear código. |
| DIV-02 | Codegen TypeScript a partir do OpenAPI (DEC-15..18) não foi implementado — `api.ts` continua manual (1086→1200 linhas). |
| DIV-03 | Endpoints antigos não delegam à nova camada (DEC-10/11) — seguem com lógica própria; ok para strangler, mas registrar. |
| DIV-04 | **Estratégia inconsistente entre BFFs**: home/health/performance são wrappers finos sobre services legados (funcionam); activities/shoes/profile usam os domínios novos **cheios de stubs** (quebrados). O strangler só é seguro no primeiro padrão. |
| DIV-05 | Tasks T13–T25 do `tasks.md` não executadas: sem `tests/bff/`, sem `tests/contract/`, sem parity tests antigo-vs-novo (T20), sem deprecação 410 (T24), sem cleanup (T25). |

Código morto remanescente no frontend (`api.ts`): `getPotential` (ERR-05), `getHealthSummary`,
`getActivities`, `getActivityDetail`, `getShoeBFF`, `getProfileZones` — nenhum componente usa;
todos apontam para superfícies novas parciais. Decidir: remover ou manter consistentes.

---

## Plano de correção (fases com checkpoint)

> **Estado atual (checkpoint):** working tree limpo na branch `refactor/backend-decoupling`
> @ `452b1e0`. Nada foi corrigido ainda. Este documento é o ponto de retomada.
> Baseline da main disponível no worktree `%TEMP%\opencode\ritmo-main`.

### F0 — Auditoria documentada ✅ (este arquivo)
**Gate:** doc revisado e acordado.

### F1 — Decisão de estratégia ✅ (02/11/2026)
**DECISÃO: Opção A — strangler real, aproveitar a branch.**

- A arquitetura (domain + BFF composição) está correta; os erros eram implementação
  incompleta (stubs/TODOs), não podridão estrutural. A main não é baseline limpa
  (suíte vermelha desde a3e89a5).
- **Regra de ouro adotada:** o BFF (e as rotas /api/v1) só apontam para implementação
  provada. Enquanto o domínio X não tiver parity test, o endpoint delega ao service
  legado. O domínio fica no repo como scaffolding e "assume" o endpoint na Fase 2,
  com parity test provando equivalência payload-a-payload.
- A ponte é invariante travada por teste: `tests/domain/test_strangler_bridges.py`
  afirma que cada rota /api/v1 é o MESMO objeto-função do handler legado.
- Quando o BFF virar serviço separado, troca-se a chamada in-process por HTTP client
  contra a API de domínio — o contrato das telas não muda.

**Gate:** decisão registrada. ✅

### F2 — Desbloquear os 404 do frontend (ERR-01..04) ✅ (02/11/2026)
- Rotas `/api/v1` agora re-registram os handlers legados (uma única implementação):
  - `POST/GET /api/v1/activities/{id}/evaluate[/{evalId}]` → `app.evaluation.router` (ERR-01)
  - `/api/v1/tenis/analysis/*` e `/api/v1/tenis/degradation/{id}` → pontes em
    `app/domain/equipment/bridge_tenis.py` (ERR-02, ERR-03)
  - `GET /api/v1/vdot` → `pace_zones_payload` do profile (shape PaceZonesOut; ERR-04)
  - `/api/v1/heart-rate-zones` (GET/PUT/history) → handlers HRZ do profile (ERR-11)
  - `/api/v1/health-metrics/summary` → handler do BFF health; `/signals` removido
- Invariante travada por `tests/domain/test_strangler_bridges.py` (rotas /api/v1 são
  os mesmos objetos-função dos handlers legados).
- Payload de degradação extraído para `app/tenis_degradation/service.py` (fonte única
  para router legado + ponte + BFF + equipment).
**Gate:** rotas novas 200/404/409 com os shapes esperados — coberto pela suíte. ✅

### F3 — BFFs apontando para implementação provada (ERR-06..12) ✅ (02/11/2026)
- BFF activities → `app.activities.service` (inferred_type/zonas/consistência/contexto/
  avaliações reais) — ERR-06..10
- BFF shoes + domínio equipment → `app.shoes.service` (current_km/run_count/last_use/
  life_pct reais, attribution) + degradação real — ERR-12
- BFF profile → `hr_zones_payload`/`pace_zones_payload` do profile — ERR-11 (contexto BFF)
- Schemas duplicados `app/bff/{activities,shoes}/schemas.py` removidos (os BFFs
  retornam os modelos legados, que SÃO o contrato de tela).
**Gate:** suíte + parity implícito (mesmos handlers do legado). ✅

### F4 — (reservado) Pipeline de domínio Activity — não iniciado
Domínio `app/domain/activity/` mantido como scaffolding (não é load-bearing). Consertar
classify/parse/km_label/context/evaluations na Fase 2 com parity tests.

### F5 — Garmin sync (ERR-13, ERR-15) ✅ (02/11/2026)
- `POST /api/v1/garmin-sync/sync` devolve 409 com o estado do job corrente (igual ao legado)
- Stubs `TokenStore`/`GarminAPIClient` e o adapter que tocava `token_encrypted`
  removidos; `SyncService` sem campos mortos; GTDB-13 restaurada
  (`test_garmin_tokens_store` verde).

### F6 — `main.py` (ERR-14) ✅ (02/11/2026)
- `include_router(..., dependencies=[Depends(require_session)])` restaurado para todos
  os routers; comentário falso "FastAPI 0.162" removido; regra documentada inline.

### F7 — Suíte de testes (HER-01..04) ✅ (02/11/2026)
- conftest: seed automático de `VdotZoneConfig` para TODO User criado em teste
  (event listener — cobre fixtures e usuários criados via HTTP register);
  fixture `no_vdot_zones` para os caminhos "sem configuração";
- `data/vdot_zones.json` regenerado via `gerar_zonas(50.2)` — CLI volta a ser a fonte
  de verdade e o arquivo volta a ser reproduzível;
- Pins de recalibração re-alinhados à fórmula fechada (51.6/49.1/51.3) — a divergência
  da fórmula vs. tabelas impressas de Daniels ficou registrada como HER-05 (decisão
  de produto pendente, fora do escopo da Fase 1);
- Removidos: `test_workouts_config.py` (testava `Settings.vdot_zones_path`, campo que
  morreu no vdot-db-only) e `test_vdot_calibration.py` (testava `load_calibration`,
  função que nunca existiu na era DB — cobertura do loader vive em `test_vdot_zones.py`);
- `test_vdot_zone_configs_model`: helper `_new_user` remove o seed automático
  (testes de model assumem tabela vazia).
**Gate:** `uv run pytest -q` → 0 failed (ver status final abaixo). ✅

### F8 — Limpeza (ERR-16, parcial) ✅ (02/11/2026)
- Removidos: `app/domain/activity/adapters/sqlalchemy_split.py` (import de pacote
  inexistente), `app/domain/*/.gitkeep` da raiz do repo, `import json` duplicado em
  `zones.py`, função morta `getPotential` no `api.ts`.
- Pendente para a Fase 2: dedupe de funções no `api.ts` (getHealthSummary/getActivities/
  getActivityDetail/getShoeBFF/getDegradation hoje funcionam mas duplicam caminhos BFF),
  codegen TS (DEC-15..18), deprecação 410 (T24).

---

## Comandos de verificação (gates)

```powershell
# Backend (raiz: backend/)
uv run pytest -q                        # alvo: 0 failed
uv run pytest tests/test_garmin_tokens_store.py -q

# Frontend (raiz: frontend/)
npx tsc --noEmit                        # deve seguir limpo

# Smoke das rotas novas (com backend no ar + cookie de sessão)
# GET  /api/v1/bff/activities            → lista com inferred_type correto
# GET  /api/v1/bff/activities/{id}       → zones com pace_range preenchido, km_label, context, evaluations
# POST /api/v1/activities/{id}/evaluate  → 201 pending (não 404)
# GET  /api/v1/heart-rate-zones          → zones derivadas (não null)
# PUT  /api/v1/heart-rate-zones          → persiste (recarregar e conferir)
# GET  /api/v1/equipment                 → current_km/life_pct reais
# GET  /api/v1/bff/shoes/{id}/degradation→ sinais reais (não stub)
# GET  /api/v1/vdot                      → shape PaceZonesOut (zones/equivalencias)
# POST /api/v1/garmin-sync/sync (2x)     → 409 na segunda chamada
```

## Riscos / observações finais

- O **SyncService novo** (462 linhas) duplica o `app/garmin/service.py` legado. Hoje funciona
  (usa o gateway legado), mas é mais uma superfície para divergir. Sugestão: reduzir a wrapper
  fino (padrão dos outros BFFs) até o domínio amadurecer.
- `app/domain/health_metrics` (`/api/v1/health-metrics/summary|signals`) é uma re-implantação
  nova do painel Saúde **sem testes e sem consumidor** (a UI usa a BFF→legado). Risco silencioso.
- `HomeTodayOut(**dict)` funciona porque o service legado devolve `dict` — se alguém trocar
  para devolver o model Pydantic, quebra em runtime (adicionar contract test).
