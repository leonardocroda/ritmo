# garmin-tokens-db Specification

## Problem Statement

Com múltiplos usuários (Fase 1.5), os tokens Garmin vivem num único tokenstore de
arquivo (`GARMINTOKENS`, mount no compose) — não escala, não isola usuários e o
refresh OAuth2 rotacionado pela lib se perde no fim do processo, matando a sessão
silenciosamente. Os tokens precisam migrar para o banco (AD-014): uma linha por
usuário, criptografados em repouso, com persistência de volta do refresh e
onboarding de convidado operador-assistido via CLI.

## Goals

- [ ] Tokens Garmin por usuário no Postgres, criptografados em repouso (Fernet) — fonte única, sem filesystem em caminho runtime
- [ ] Refresh OAuth2 persistido de volta no banco — sessão sobrevive à rotação do refresh token
- [ ] Onboarding de convidado = 1 comando CLI operador-assistida (`--user <email>`, MFA interativo)
- [ ] Tokenstore de arquivo extinto: mount do compose, `GARMINTOKENS`/`GARMINTOKENS_BASE64` e code morto removidos

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Fluxo web de credenciais Garmin (login na UI) | Fase 2.5 (AD-014): MFA interativo exige CLI; convidado nunca digita senha Garmin no site (§10.6) |
| Botão Desconectar / exclusão de tokens via UI | Decisão do usuário (21/10): /perfil é só exibição; revogação é operação de operador (SQL/CLI) no MVP |
| Rotação de `TOKEN_ENCRYPTION_KEY` / re-criptografia em massa | Chave é segredo de ambiente do operador; rotação = re-login de cada usuário (aceitável no MVP) |
| Compartilhamento ou transferência de tokens entre usuários | 1 conta Garmin = 1 usuário, sempre |
| HTTPS / cookie Secure | Fase 2.5 (AD-013) |
| Alembic para a nova tabela | AD-019: evolução de schema = ALTERs idempotentes no `init_db` |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Fonte do blob | JSON `dumps()` da lib (di_token/di_refresh_token/di_client_id), cifrado como valor opaco | Formato da lib pinada 0.3.2 (spike no código instalado); mudança de formato = re-login, aceitável | y |
| Chave Fernet gerada e distribuída manualmente via `.env`/compose | `TOKEN_ENCRYPTION_KEY` no `.env`, gerada por `Fernet.generate_key()` | Segredo de operador, igual `INVITE_CODE`/`NVIDIA_API_KEY`; rotação fora de escopo | y |
| Blob que não decripta (chave trocada/perdida) | Tratado como tokens ausentes → estado "Reconectar" | Sem caminho de recuperação; operador refaz login CLI | n |
| Guard de corrida do persist-back | A linha guarda `updated_at`; o persist-back só grava se a linha não mudou desde o carregamento | Evita que o sync derrube um re-login CLI feito durante o job (rotacionado ≠ atual) | n |
| Endpoint de status deriva do último job do usuário | Sem nova tabela de estado; mesma fonte que a UI de sync já consome | Estado "Reconectar" hoje já vive em `stats.reauth_needed` (SYNC-25) | n |
| Env legada `GARMINTOKENS_BASE64` sai junto com `GARMINTOKENS` | Mesma remoção, mesmo motivo | Herança da era MCP, sem leitor no app | n |
| CLI de login mantém o fluxo atual da lib (5 estratégias + `prompt_mfa`) | Só muda o destino dos tokens: arquivo → banco cifrado | Fluxo provado em produção; MFA interativo é requisito (AD-014) | y |
| Importação do legado é CLI run-once, não seed automático no `init_db` | `python -m app.garmin.import_tokens` roda no host, lê o arquivo e grava cifrado | Container não vê o home do host sem o mount — e o mount morre nesta feature (decisão "remover de vez") | y |
| Tokenstore de arquivo removido de vez (decisão 21/10) | Compose, `.env.example`, README e envs limpos nesta feature; único leitor legítimo do arquivo é o CLI de importação | Fonte única = banco | y |
| `TOKEN_ENCRYPTION_KEY` ausente/inválida = fail-fast (decisão 21/10) | Backend não sobe, com mensagem clara | Sem a chave é impossível ler tokens nem garantir criptografia em repouso | y |
| /perfil: seção Conexão só exibição (decisão 21/10) | 3 estados, sem ação | Re-login permanece CLI | y |

**Open questions:** none - all resolved or logged above (required before the spec is confirmed).

---

## User Stories

### P1: Sync lê tokens do banco por usuário ⭐ MVP

**User Story**: As a corredor conectado, I want o meu sync a usar os MEUS tokens do banco so that a sessão Garmin seja isolada por usuário e sobreviva a deploys/restarts.

**Why P1**: É o núcleo da AD-014 — sem isso, multiusuário é impossível (todo mundo usaria o tokenstore único) e todo restart perde o refresh rotacionado.

**Acceptance Criteria** (each line is one EARS pattern):

1. WHEN o job de sync de um usuário inicia THEN o sistema SHALL hidratar a sessão Garmin exclusivamente dos tokens daquele usuário no banco, decriptados em memória (nenhuma leitura de filesystem no caminho runtime)  <!-- event-driven -->
2. The system SHALL manter exatamente uma linha de tokens por usuário (unique `user_id`, FK com CASCADE — deletar o usuário apaga os tokens)  <!-- ubiquitous -->
3. IF o usuário não tem tokens no banco, ou o blob não decripta, ou o blob não contém as credenciais que a lib exige THEN o job SHALL terminar `error` com `reauth_needed=true` (estado "Reconectar Garmin" atual, SYNC-25)  <!-- unwanted-behavior -->

**Independent Test**: Com tokens do usuário 1 importados e o mount do compose removido, disparar sync e vê-lo concluir `done`; com o usuário 2 (sem tokens), disparar sync e vê-lo `error` com `reauth_needed=true` sem tocar a API real (lib stubada).

---

### P1: Refresh persistido de volta no banco

**User Story**: As a corredor, I want o refresh OAuth2 ser gravado de volta no banco so that minha sessão Garmin não morra silenciosamente quando o refresh token rotaciona.

**Why P1**: Hoje a persistência de volta só existe no tokenstore de arquivo (`_tokenstore_path`); com blob inline a lib NÃO persiste — o persist-back precisa ser nosso (spike: `_refresh_di_token` pode rotacionar o refresh token).

**Acceptance Criteria**:

1. WHEN o job de sync encerra (qualquer status exceto `error` com `reauth_needed`) THEN o sistema SHALL garantir que a linha do banco contém o blob vigente da sessão do gateway, cifrado  <!-- event-driven -->
2. IF os tokens do usuário mudaram no banco depois que o gateway os carregou (ex.: re-login CLI durante o sync) THEN o persist-back SHALL não sobrescrever a linha mais nova  <!-- unwanted-behavior -->
3. IF o persist-back falha THEN o sync SHALL concluir normalmente e registrar warning nos stats (o risco assumido é reauth no ciclo seguinte, nunca perda do sync)  <!-- unwanted-behavior -->

**Independent Test**: Lib fake cujo `dumps()` muda após o primeiro request → ao fim do job, o blob no banco é o novo; simulando mudança concorrente na linha (re-login fake), o persist-back recusa e os tokens novos permanecem.

---

### P1: Login de convidado via CLI operador-assistida

**User Story**: As a operador, I want conectar a conta Garmin de um convidado com um comando CLI so that ele nunca digite a senha Garmin no site e o MFA interativo funcione.

**Why P1**: É o único caminho de onboarding Garmin do MVP (AD-014); sem ele, o segundo usuário não existe na prática.

**Acceptance Criteria**:

1. WHEN o operador roda `python -m app.garmin.login --user <email>` com credenciais válidas e MFA THEN o sistema SHALL gravar (upsert) os tokens cifrados na linha do usuário daquele email  <!-- event-driven -->
2. IF o email não pertence a nenhum usuário THEN o CLI SHALL terminar com erro claro e não gravar nada  <!-- unwanted-behavior -->
3. IF o login falha (credenciais erradas, MFA errado, rate limit) THEN o CLI SHALL terminar com erro e os tokens existentes do usuário SHALL permanecer inalterados  <!-- unwanted-behavior -->

**Independent Test**: Com a lib stubada, o CLI cria/atualiza a linha do usuário-alvo; email inexistente e login que falha não alteram nenhuma linha.

---

### P1: Importação run-once dos tokens do usuário 1

**User Story**: As a operador, I want importar os tokens atuais do usuário 1 do tokenstore legado sem refazer MFA so that a transição não custa re-login.

**Why P1**: Decide a fila sem zero-touch: o container não vê o home do host, então o seed automático no `init_db` é inviável sem manter o mount — que morre nesta feature.

**Acceptance Criteria**:

1. WHEN o operador roda `python -m app.garmin.import_tokens` com o tokenstore legado presente THEN o sistema SHALL importar e cifrar os tokens na linha do usuário 1  <!-- event-driven -->
2. IF o usuário 1 já tem tokens no banco THEN o comando SHALL recusar com orientação para usar o login CLI, sem alterar a linha (idempotente por omissão — nunca reimportar token velho sobre token novo)  <!-- unwanted-behavior -->
3. IF o arquivo legado não existe ou é ilegível THEN o comando SHALL terminar com erro claro e não gravar nada  <!-- unwanted-behavior -->

**Independent Test**: Com um tokenstore fake no path apontado, o comando grava a linha cifrada do usuário 1; rodando de novo, recusa; sem arquivo, erro sem gravação.

---

### P1: Criptografia em repouso com fail-fast

**User Story**: As a operador, I want os tokens cifrados com Fernet sob `TOKEN_ENCRYPTION_KEY` e o backend recusando a subida sem a chave so that vazamento do dump do banco não vaze credenciais e o app nunca rode num estado impossível.

**Why P1**: Criptografia em repouso é o requisito de segurança central da AD-014; fail-fast evita sync "funcionando" com segredo ausente em produção silenciosa.

**Acceptance Criteria**:

1. The system SHALL armazenar todo blob de token exclusivamente cifrado (Fernet sob `TOKEN_ENCRYPTION_KEY`) — nenhuma coluna ou log com texto plano  <!-- ubiquitous -->
2. IF `TOKEN_ENCRYPTION_KEY` estiver ausente ou não for uma chave Fernet válida no startup THEN o backend SHALL interromper a subida com mensagem clara apontando a correção  <!-- unwanted-behavior -->
3. The system SHALL nunca registrar conteúdo de token ou blob (cifrado ou não) em logs, stats, mensagens de erro ou respostas de API  <!-- ubiquitous -->

**Independent Test**: `SELECT` na tabela mostra só ciphertext (inspecionável no teste); `.env` sem a chave derruba a subida com a mensagem esperada; grep na saída de logs/stats dos testes não encontra fragmento de token.

---

### P2: Status da conexão no /perfil (só exibição)

**User Story**: As a corredor, I want ver no /perfil o estado da minha conexão Garmin so that saber se o sync está saudável ou se preciso pedir reconexão ao operador.

**Why P2**: A informação existe hoje espalhada (estado do sync na tela de treinos); centralizar no /perfil fecha o loop do usuário sem ação nova (re-login é CLI por decisão).

**Acceptance Criteria**:

1. WHEN a página /perfil carrega THEN a seção Conexão SHALL exibir exatamente um dos estados: "Conectado" (linha de tokens existe e não há reautenticação pendente), "Reautenticação necessária" (o último job do usuário terminou com `reauth_needed=true` e os tokens NÃO foram atualizados depois do fim desse job — re-login posterior volta a exibir "Conectado") ou "Não conectado" (sem linha de tokens)  <!-- event-driven -->
2. The endpoint de status SHALL responder apenas para o usuário da sessão (401 sem sessão, padrão existente) e SHALL conter apenas metadados (estado, data da última alteração dos tokens) — nunca o blob  <!-- ubiquitous -->

**Independent Test**: GET autenticado devolve o estado correto para os três cenários (com tokens, com último job reauth, sem tokens); o JSON não contém nenhum fragmento de token.

---

### P2: Tokenstore de arquivo extinto

**User Story**: As a mantenedor, I want o tokenstore de arquivo e seu code morto removidos so que haja uma única fonte de verdade e zero leitura de credenciais em caminho runtime.

**Why P2**: É a "remoção de vez" decidida — sem ela o banco e o arquivo convivem e o bug de sessão duplicada volta.

**Acceptance Criteria**:

1. WHEN a feature está no ar THEN o compose SHALL não montar `~/.garminconnect` e o `.env.example`/README SHALL não referenciar `GARMINTOKENS` nem `GARMINTOKENS_BASE64`  <!-- event-driven -->
2. The backend SHALL não ler tokenstore de arquivo em nenhum caminho runtime — o único leitor legítimo do arquivo legado é o CLI de importação (P1 anterior)  <!-- ubiquitous -->
3. WHEN o cleanup roda THEN `token_utils.py` SHALL reter apenas as funções em uso e as funções mortas da era MCP (`validate_tokens`, `remove_tokens`, `get_token_info`, `get_token_base64_path`, `token_exists`) SHALL estar removidas com a suite verde  <!-- event-driven -->

**Independent Test**: Grep no repositório não encontra `GARMINTOKENS` fora do CLI de importação; `docker compose config` não contém o mount; suite verde sem os nomes removidos.

---

## Edge Cases

- IF a chave `TOKEN_ENCRYPTION_KEY` for trocada/perdida com tokens gravados THEN o sistema SHALL tratar o blob ilegível como tokens ausentes → estado "Reconectar" (nunca crash do sync) — coberto por GTDB-03
- IF o operador re-loga um usuário durante o sync dele THEN o persist-back SHALL preservar os tokens novos (GTDB-04 AC 2)
- IF o blob inline não satisfaz o mínimo que a lib exige (chaves ausentes) THEN o resultado é equivalente a tokens ausentes → `reauth_needed` (GTDB-03 AC 3)
- WHEN o usuário é deletado THEN os tokens SHALL ser deletados junto (FK CASCADE, padrão `sessions`)
- IF dois processos tentam persistir tokens do mesmo usuário simultaneamente (sync + CLI) THEN a última escrita válida vence com o guard de corrida (GTDB-04 AC 2); lock de sync por usuário já impede dois syncs (SYNC-02)

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| GTDB-01 | P1: Sync lê tokens do banco | Design | ✅ Verified |
| GTDB-02 | P1: Sync lê tokens do banco | Design | ✅ Verified |
| GTDB-03 | P1: Sync lê tokens do banco | Design | ✅ Verified |
| GTDB-04 | P1: Refresh persistido de volta | Design | ✅ Verified |
| GTDB-05 | P1: Refresh persistido de volta | Design | ✅ Verified |
| GTDB-06 | P1: Refresh persistido de volta | Design | ✅ Verified |
| GTDB-07 | P1: Login de convidado via CLI | Design | ✅ Verified |
| GTDB-08 | P1: Login de convidado via CLI | Design | ✅ Verified |
| GTDB-09 | P1: Login de convidado via CLI | Design | ✅ Verified |
| GTDB-10 | P1: Importação run-once do usuário 1 | Design | ✅ Verified |
| GTDB-11 | P1: Importação run-once do usuário 1 | Design | ✅ Verified |
| GTDB-12 | P1: Importação run-once do usuário 1 | Design | ✅ Verified |
| GTDB-13 | P1: Criptografia em repouso com fail-fast | Design | ✅ Verified |
| GTDB-14 | P1: Criptografia em repouso com fail-fast | Design | ✅ Verified |
| GTDB-15 | P1: Criptografia em repouso com fail-fast | Design | ✅ Verified |
| GTDB-16 | P2: Status da conexão no /perfil | - | ✅ Verified |
| GTDB-17 | P2: Status da conexão no /perfil | - | ✅ Verified |
| GTDB-18 | P2: Tokenstore de arquivo extinto | - | ✅ Verified |
| GTDB-19 | P2: Tokenstore de arquivo extinto | - | ✅ Verified |
| GTDB-20 | P2: Tokenstore de arquivo extinto | - | ✅ Verified |

**Coverage:** 20 total, 20 mapped to tasks, 0 unmapped ✅

---

## Success Criteria

- [ ] Sync do usuário 1 conclui `done` com o mount do compose removido — tokens só no banco
- [ ] `SELECT` na tabela de tokens mostra apenas ciphertext (nada em plano)
- [ ] Um convidado novo fica on-boardável com 1 comando CLI (`--user <email>`) e zero coleta de credencial no site
- [ ] Refresh token rotacionado durante o sync é encontrado na linha do banco ao fim do job
- [ ] Suite verde (incl. testes de isolamento por usuário); zero leitura de filesystem em caminho runtime; `GARMINTOKENS` ausente do repositório fora do CLI de importação
