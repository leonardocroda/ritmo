# Plano — Plataforma Pessoal de Corrida com IA

> Documento de planejamento · Out/2026
> Usuário inicial: eu (Leonardo) · Objetivo: pensar e ver a corrida de um só lugar

---

## 1. Contexto — o que já existe e o que já foi aprendido

Este projeto já tem ativos valiosos que a plataforma reaproveita:

| Ativo | O que é | Como a plataforma usa |
|---|---|---|
| `garmin_mcp` (servidor MCP) | 153 ferramentas sobre a API do Garmin Connect via lib `garminconnect` 0.3.2 | Fonte de dados: o botão "Puxar do Garmin" usa a **mesma lib por trás do MCP** |
| `analyze-garmin-run` (skill) | Framework de avaliação: execução vs intenção, zonas VDOT + FC, contexto (clima/sono/HRV), regras de veredito | Vira o **system prompt** do motor de avaliação IA |
| `calibrate-garmin-zones` (skill) | Entrevista + equações de Jack Daniels → `vdot_zones.json` (VDOT 50.2, teste 10K 41:15 em 03/10/2026) | Feature de calibração de zonas + arquivo de zonas como fonte de verdade |
| `create-garmin-training` (skill) | Monta treinos estruturados (RepeatGroupDTO) e agenda no Garmin Connect | Feature futura: "montar treino" a partir da recomendação da IA |
| `generate-run-summary-image` (skill) | Story 1080×1920 com gráfico pace+FC via Playwright | Feature futura: gerar imagem do treino avaliado |

**Perfil do usuário (dos dados reais):** 28 anos, VDOT 50,2 (limiar real estimado 4:08–4:12/km, LTHR 177), RHR 43–45, HRV ~77ms, sono médio 6h17 (83% das noites <7h, REM 14%), yoga 3×/sem, força ~1×/sem (alvo 2×), ~52 km/semana. Próximos objetivos: meia The Best Açaí 08/11/2026 (alvo ~1:29:3x) → bloco 10K sub-40 em janeiro.

**Lições de arquitetura aprendidas nas sessões passadas (viram requisitos):**

1. **A API do Garmin cai com rajadas de chamadas** (~40 chamadas paralelas derrubaram o login e exigiram re-auth com MFA). → A plataforma **nunca** consulta o Garmin ao renderizar tela: sync explícito (o botão), sequencial, com backoff, e **banco próprio** como fonte da UI.
2. **Re-auth com MFA é evento esperado** → botão "Reconectar Garmin" e mensagens claras quando o token expira.
3. **Hierarquia de confiança das métricas** (da sessão de errata): ritmo/GPS e provas > FC de pulso. FC óptica serve como corroboração, não como veredito. O motor de análise segue essa hierarquia.
4. **Intenção importa mais que os números** — a avaliação só existe se souber a intenção do treino (fácil rápido demais é erro, mesmo sendo "impressionante").
5. **Padrões de falha pessoais documentados**: largar rápido demais (km 1 mais rápido que a média em 100% das provas máximas), fade nos km 15–19 da meia, parede no km 26 da maratona (combustível + força + FC), sono ruim às vésperas. → O produto rastreia esses padrões explicitamente.

---

## 2. Visão

> **"Pensar e ver a corrida de um só lugar"** — gráficos simples que entregam as métricas certas, um retrato honesto do meu potencial e da minha evolução, sono/saúde de verdade, e cada treino avaliado por IA quando *eu* pedir.

Princípios:

- **Local-first, um usuário** (eu). Deploy no meu PC; acesso no celular pela rede local (o `perfil_corredor.html` já provou o desejo).
- **Garmin só no sync.** Toda a UI lê do banco próprio (rápido, sem rate-limit, funciona offline).
- **IA sob demanda.** Nada de avaliar automático — o botão "Avaliar" existe porque avaliação tem custo (tokens) e valor (só quando quero).
- **Simplicidade de leitura > quantidade de gráficos.** Cada painel responde uma pergunta; se o gráfico não responde uma pergunta minha, não entra.

---

## 3. Panorama do mercado (pesquisa, out/2026)

| Plataforma | O que faz bem | O que NÃO faz (meu gap) |
|---|---|---|
| **Garmin Connect (+Connect+)** | Training Status, Body Battery, Load Focus, previsões, PacePro, "Active Intelligence" (IA) | Análise genérica, sem intenção do treino, sem VDOT personalizado, não explica "por quê" |
| **TrainingPeaks** (~US$20/mês) | PMC (CTL/ATL/TSB), TSS, treino estruturado → relógio, coaches | Sem avaliação conversacional; sobrecarregado p/ uso pessoal |
| **Runalyze** (grátis) | VO2max efetivo, prognóstico de provas, análise profunda | UI datada, sem intenção, sem IA |
| **Intervals.icu** (grátis) | Fitness/fadiga, detecção automática de intervalos, push p/ relógio | Sem avaliação por IA com contexto de intenção |
| **Runna** (US$20/mês, comprada pela Strava) | Planos adaptativos 5K→maratona, relógio, audio coach | Plano rígido de treino; não avalia execução vs intenção; load analytics raso |
| **Strava** (Athlete Intelligence) | Social + resumos de atividade por IA | Resumo descritivo, não avaliação de execução |
| **Tredict** | MCP server p/ IA planejar dentro da plataforma → Garmin | Foco em planejamento, não em avaliação de execução |
| **AthleteData.health** | "AI coach messages you first" (Telegram/WhatsApp), zonas dinâmicas Morpheus (±5% por HRV/RHR) | Fechado, sem calibração VDOT própria, sem meus dados |

**Conclusão da pesquisa:** ninguém faz bem o que as skills deste projeto já fazem conversacionalmente — **avaliar a execução de um treino contra a intenção declarada, com zonas VDOT minhas + contexto fisiológico + padrões de falha pessoais**. A diferenciação da plataforma não é inventar análise; é **produtozificar** a metodologia que já existe nas skills, com os dados num banco próprio e gráficos que respondem perguntas.

---

## 4. O produto — 4 painéis + 2 botões

### 4.1 Botão 1 — "Puxar do Garmin" (sync)

- Usa a lib `garminconnect` (a mesma por trás do MCP), reutilizando os tokens já salvos (`token_utils.py`).
- Puxa desde o último sync: atividades (com splits/laps), sono, HRV, RHR, body battery, estresse, carga de treino, previsões, recordes.
- **Sequencial + backoff** (nunca paralelo — lição nº 1). Um job de sync com status visível ("Puxando 12 atividades…").
- Incremental: guarda `last_sync` por tipo de dado; re-puxa os últimos N dias para pegar edições tardias (Garmin reprocessa sono/carga por até 72h).
- Botão "Reconectar Garmin" quando o token morrer (re-auth MFA manual).

### 4.2 Painel "Hoje" (readiness + semana)

Pergunta: **"Como estou e o que importa hoje?"**

- Card do dia: HRV status (balanced/unbalanced vs baseline), sono da última noite vs minha média, RHR vs 7d, Body Battery, carga aguda/crônica (ACWR) + TSB.
- Countdown da prova-alvo (The Best Açaí 08/11 · meta 1:29:3x) com % do bloco concluído.
- Semana atual: treinos planejados vs executados, volume acumulado vs média das últimas 4 semanas.
- Alertas que seguem minhas regras: "HRV UNBALANCED 2+ manhãs antes de dia de qualidade → trocar por leve"; "sono <6h na véspera de treino forte"; "força 2×/semana em falta".

### 4.3 Painel "Treinos" (lista + detalhe do treino)

Pergunta: **"Como foi esse treino, de verdade?"**

Lista (data, tipo inferido, distância, ritmo, FC, alvo ✅⚠️❌ se avaliado, badge "avaliado").

Detalhe do treino:

1. **Gráfico de splits** — barras de ritmo por km coloridas por zona VDOT (verde=easy, azul=marathon, laranja=threshold, vermelho=interval, roxo=repetition) + linha de FC + relevo. É a visualização central: fácil de ler e julga pacing à primeira vista. (Base: o gráfico do `generate-run-summary-image`, que já está validado.)
2. **Execução vs intenção** (aparece só se avaliado): % de tempo na zona alvo, splits fora da faixa, veredito ✅⚠️❌.
3. **Métricas de consistência** (tabela p/ ≥8km): split equilibrado (1ª vs 2ª metade), drift cardíaco (bpm a ritmo constante), fade de cadência, decoupling FC/pace.
4. **Faixa de contexto**: clima, elevação, sono, HRV, RHR, readiness — só o que existir.
5. **Card de avaliação IA** (ver 4.6) + histórico de avaliações.
6. Botão "Gerar story" (fase 2): reaproveita `generate_image.py` injetando o veredito.

### 4.4 Painel "Potencial" (a pergunta: "qual meu máximo e a que distância dele estou?")

- **Linha do tempo VDOT**: cada teste/prova máxima vira um ponto (VDOT calculado); linha com o VDOT "corrente" calibrado (50,2) e a faixa honesta (seu 5K de 19:23 equivale a VDOT ~53). Mostrar a **lacuna**: quanto do meu potencial demonstrado já está "liberado" no teste de referência.
- **Previsões vs PRs**: minhas 4 estimativas lado a lado (Garmin, Riegel do último resultado, equivalência VDOT, e a média honesta) para 5K/10K/meia/maratona + PR histórico. O alvo da próxima prova plota no gráfico.
- **Curva fitness/fadiga** (PMC): CTL, ATL, TSB — o clássico, porque funciona.
- **Decay de ritmo por distância**: pace do 5K→10K→meia→maratona vs decay "ideal" — mostra que sou 5K–meia e que maratona é gap de execução/especificidade, não de motor.
- **Tendência VO2max** (relógio) com a ressalva visual de "estimativa" (hierarquia de métricas: provas/testes > algoritmo).

### 4.5 Painel "Saúde" (sono e recuperação)

Pergunta: **"Meu corpo está absorvendo o treino?"**

- **Sono**: duração vs piso 7h (linha no gráfico — o gráfico de "quantas noites abaixo do piso"), score, **REM %** (minha assinatura: 14% vs ideal 21–31%), horário de dormir/acordar (regularidade ±min), debt acumulado no mês. Padrão por dia da semana (minha sexta é o buraco).
- **HRV noturno**: linha 60d + status; RHR: linha vs baseline.
- **Dose-resposta pessoal** (o gráfico que provou o ponto na análise de saúde): noites <6h → HRV/score médios vs noites ≥6h45. Meu corpo cobra juros visíveis — mostrar isso me convence a dormir.
- **Equilíbrio de vida**: força 2×/sem (streak), yoga (mantém como está), passos/NEAT nos dias de escritório, estresse médio.
- Correlações simples: sono × HRV do dia seguinte × FC do treino.

### 4.6 Botão 2 — "Avaliar com IA" (motor de avaliação)

Fluxo:

1. No detalhe do treino, campo de **intenção**: tipo (fácil / tempo / limiar / intervalado / longão / progressivo / prova) + texto livre ("era pra ser 30min a 4:15").
2. O backend monta o **payload determinístico em Python** (sem LLM): classificação de cada split por zona VDOT, % tempo por zona de FC (config RUNNING), drift, decoupling, splits 1ª/2ª metade, relevo por split, + contexto (clima, sono, HRV, RHR, readiness, ACWR) + zonas atuais + PRs + padrões pessoais.
3. Uma chamada **NVIDIA NIM** (`https://integrate.api.nvidia.com/v1/chat/completions`, OpenAI-compatível, API key do build.nvidia.com — a mesma conta que já uso no OpenCode) com o system prompt derivado de `analyze-garmin-run` (intent-first, regras de veredito, hierarquia de métricas, resposta em PT-BR no formato de card).
4. Resposta em JSON estruturado (veredito, execução vs intenção, o que funcionou, o que corrigir, contexto relevante, confiança) + texto amigável. Salva no banco com modelo, versão do prompt, tokens e data.
5. UI mostra o card; veredito alimenta o painel Potencial e o histórico ("últimas 10 avaliações: 7 no alvo, 2 acima, 1 abaixo").

Modelo: `z-ai/glm-5.3` (o que uso hoje) para vereditos; modelos *flash* (glm-5.3-flash / deepseek-v4.1-flash) como opção econômica para análises leves. Configurável por avaliação.

Por que o cálculo pesado é em Python e não no LLM: determinístico, auditável, sem alucinação de números, e o prompt fica pequeno (menos tokens, mais barato). O LLM faz o que LLM faz bem: interpretar, pesar contexto, dar o veredito e a recomendação.

---

## 5. Arquitetura

```
┌────────────────────────────────────────────────────────┐
│  Frontend (Next.js + Tailwind + Recharts/ECharts)      │
│  mobile-first, rodando no PC (acesso via rede local)   │
└───────────────┬────────────────────────────────────────┘
                │ REST/JSON
┌───────────────▼────────────────────────────────────────┐
│  Backend FastAPI (Python)                              │
│  /sync ───────────► garminconnect (lib do MCP)         │
│  /activities,/health,                                   │
│  /potential ──────► lê SQLite (nunca o Garmin direto)   │
│  /evaluate ───────► payload determinístico ──► NIM API  │
│  /zones ──────────► calibração VDOT (port da skill)    │
└───────────────┬───────────────────┬───────────────────┘
                │                   │
      ┌─────────▼────────┐   ┌──────▼───────────────┐
      │ SQLite (ou PG)   │   │ NVIDIA NIM API        │
      │ activities, splits│   │ integrate.api.nvidia  │
      │ sleep, hrv, rhr…  │   │ .com/v1/chat/completions│
      │ vdot, evaluations │   │ (key: build.nvidia.com)│
      └──────────────────┘   └──────────────────────┘
```

- **Backend**: FastAPI — mesma stack do projeto; reusa `garminconnect`, `token_utils`, e porta `calibrate_vdot.py` e as métricas da skill de análise para funções puras testáveis.
- **Banco**: SQLite (WAL) na v1 — zero ops. Migrar p/ Postgres só se multiusuário.
- **Frontend**: Next.js + Recharts (ou ECharts p/ o gráfico de splits com as cores por zona). Gráficos de linha/barras simples, tema escuro, cards grandes no celular.
- **Jobs**: sync como job em background (FastAPI BackgroundTasks na v1; RQ/Celery se escalar).
- **Segredos**: `.env` com `NVIDIA_API_KEY` e credenciais Garmin (já existem os tokens do MCP).
- **Custo IA**: avaliação ≈ 10–30k tokens in / 1–2k out. No build.nvidia.com (créditos de inferência) o uso pessoal é marginal; registrar tokens por avaliação desde o dia 1 para o futuro.

### Modelo de dados (essencial)

```
activities(id, garmin_id, data, tipo, nome, distância, tempo, pace, fc_méd, fc_máx,
           cadência, potência, elevação, te_aeróbico, te_anaeróbico, carga, feel, rpe,
           raw_json, avaliado)
splits(activity_id, ordem, dist_m, duração_s, pace_s, fc, elevação, intensity_type)
sleep(data, duração, score, deep_pct, rem_pct, light_pct, despertares, deitar, acordar)
hrv(data, valor, status)   rhr(data, valor)   body_battery(data, valor)   stress(data, méd)
load(data, ctl, atl, tsb, acwr, load_focus…)
vdot_tests(data, distância, tempo, vdot, fonte)     zones(id, json, vigência)
evaluations(id, activity_id, intent_type, intent_text, payload_json, model, prompt_version,
            verdict, verdict_json, tokens_in, tokens_out, criado_em)
races(id, nome, data, distância, meta, resultado, vdot_estimado)
patterns(id, nome, gatilho, descrição)  -- padrões de falha pessoais ("km1_rápido", "fade_15_19")
```

---

## 6. Roadmap

### Fase 0 — Decisões + esqueleto (fim de semana)
- [x] Decidir stack do frontend e nome do projeto → **Next.js + Recharts** · nome: **Ritmo** (14/10/2026)
- [x] Repo + esqueleto FastAPI + SQLite + schema + auth Garmin (tokens existentes) (14/10/2026)

### Fase 1 — MVP (2–3 fins de semana)
> Meta: substituir o "pedir análise no OpenCode" para o dia-a-dia.

**Requisitos de arquitetura (travados — ver seção 10):**
- [ ] `user_id` em todas as tabelas (usuário único default)
- [ ] SQLAlchemy (SQLite→Postgres = connection string)
- [ ] Sync como job isolado `SyncJob(user_id, janela)` (in-process na v1)
- [ ] `model`/`prompt_version`/tokens gravados em toda avaliação
- [ ] Config 100% por env vars

**Features:**
- [ ] Botão **Puxar do Garmin** (atividades + splits + sono/HRV/RHR + carga) com sync incremental e status
- [ ] Lista de treinos + **detalhe com gráfico de splits** (cores por zona VDOT + linha FC + relevo)
- [ ] Painel **Potencial**: timeline VDOT, previsões vs PRs, PMC
- [ ] Painel **Saúde**: sono (duração vs 7h, REM), HRV, RHR, dose-resposta sono
- [ ] Botão **Avaliar com IA**: intenção → payload → NIM → card de veredito salvo
- [ ] Painel Hoje: readiness + countdown da prova + semana

### Fase 2 — Fechando o ciclo (após a meia de 08/11)
- [ ] **Revisão semanal por IA** (série de treinos: tendências, carga, sono × execução)
- [ ] Histórico de avaliações + % no alvo por tipo de treino (meus padrões de falha em gráfico)
- [ ] **Gerar story** no detalhe do treino (reuso do `generate_image.py` com o veredito injetado)
- [ ] Calibração de zonas no app (port da entrevista VDOT) + alerta "novo teste? recalibrar"
- [ ] Alertas proativos (HRV 2+ dias, sono véspera, força 2×)
- [ ] "Montar treino" (reuso do `create-garmin-training`): da recomendação da IA → treino no Garmin Connect

### Fase 2.5 — Teste controlado (nuvem, 5–20 convidados)

> Gatilho: 90 dias de uso próprio sólido + pedido de amigos. Não é a Fase 3 — é um ensaio dela.

- [ ] Deploy: `docker-compose` (app + worker + Postgres + Redis) em VPS barata (Hetzner/Fly.io/Render) + HTTPS
- [ ] Auth de usuários (Supabase Auth / Clerk — dia de trabalho)
- [ ] `user_id` propagado nas queries + isolamento por usuário (ver seção 10)
- [ ] Sync por fila (RQ/arq + worker separado), 1 job por usuário, lock por sessão Garmin
- [ ] Cofre de tokens Garmin criptografados em repouso (LGPD: são dados de saúde de terceiros)
- [ ] Chave NVIDIA única da plataforma + cota por usuário (o registro de tokens da v1 vira o medidor)
- [ ] Disclaimer claro: beta privado, dados deletáveis, como desconectar (apagar tudo)

### Fase 3 — Se um dia escalar
- [ ] Multiusuário: sync por fila (workers), rate-limit por usuário, observabilidade
- [ ] **Fonte Garmin**: `garminconnect` é API não-oficial (risco de ToS/quebra) → para mercado, avaliar **Garmin Health API oficial** (programa de parceiro, review, custo) ou **Strava API oficial** (OAuth simples, mas sem sono/HRV/body battery) ou upload de FIT
- [ ] **Cobrança por uso**: BYO key (NVIDIA/OpenAI/Anthropic) ou key da plataforma com Stripe metered — os registros de tokens da v1 viram a base da cobrança
- [ ] App mobile (PWA primeiro) + notificações (o caminho do AthleteData.health: WhatsApp/Telegram)

---

## 7. Riscos e mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| API Garmin não-oficial muda/limita | Sync quebra | Banco próprio já guarda tudo; sync incremental + backoff; export/backup do SQLite |
| Rate-limit / bloqueio SSO (já aconteceu) | Sem dados novos | Fila sequencial, retry com backoff, botão reconectar, nunca paralelo |
| Custo de tokens se escalar | Margem | Tokens por avaliação desde a v1; modelos flash p/ tarefas leves; cache de veredito (não reavaliar o mesmo treino sem pedir) |
| LLM alucinar número | Veredito errado | Números calculados em Python; LLM só interpreta; veredito estruturado com "evidências" referenciando splits |
| Overengineering | Projeto morre antes do MVP | Fase 1 = 6 telas + 2 botões; nada de multiusuário antes de 90 dias de uso próprio |

---

## 8. Decisões fechadas (13/10/2026)

1. **Frontend**: ✅ **Next.js + Recharts** (mobile-first, tema escuro) — o diferencial é a experiência de ver os dados.
2. **Escopo da Fase 1**: ✅ **MVP completo** — 6 telas + 2 botões (sync, treinos, potencial, saúde, avaliação IA, painel Hoje).
3. **Gráfico de splits**: portar a lógica de cores por zona do `generate_image.py` para Recharts (composto: barras de pace + linha de FC + relevo no eixo secundário).
4. **Nome**: a definir na Fase 0 (candidatos: "Zona", "Lactato", "RunBrain").
5. **Onde roda**: PC + acesso LAN no celular (v1) — deploy em nuvem só se quiser consultar fora de casa.
6. **Avaliação em lote**: fica na Fase 2 como "revisão semanal" (custo de tokens por design).

## 9. Refinamento fechado (13/10/2026) — conteúdo das telas e motor de avaliação

### 9.1 Composição exata dos painéis (v1)

| Painel | Entra na v1 | Fica cortado (vai depois) |
|---|---|---|
| **Hoje** | Card de readiness (HRV status + sono da última noite vs média + RHR vs 7d + ACWR/TSB) · countdown da prova-alvo · semana planejada vs executada · volume vs média 4 semanas | Alertas proativos (Fase 2) |
| **Treinos** | Lista (data, tipo inferido, distância, pace, FC, badge de avaliação) → detalhe com **1 gráfico** (barras de pace por zona VDOT + linha FC + relevo) + métricas de consistência (≥8km: split 1ª/2ª metade, drift, cadência, decoupling) + faixa de contexto + card de avaliação IA | Mapa do trajeto · comparação lado-a-lado |
| **Potencial** | Timeline VDOT (provas/testes + VDOT corrente + faixa honesta) · previsões vs PRs (4 estimativas + alvo da próxima prova plotado) · PMC (CTL/ATL/TSB) | Decay por distância (v1 mostra o número, sem gráfico dedicado) |
| **Saúde** | Sono: duração vs linha de 7h + score + **REM%** + regularidade (deitar/acordar) + padrão por dia da semana · HRV/RHR linhas · **dose-resposta sono→HRV/score** (noites <6h vs ≥6h45) · checklist de vida (força 2×, yoga, NEAT) | Correlações avançadas |

### 9.2 Estrutura do veredito da IA (JSON retornado pelo LLM)

```json
{
  "veredito": "on_target | too_hard | too_easy | context_explained | fatigue_signal",
  "headline": "Execução quase perfeita no bloco de limiar",
  "execucao_vs_intencao": {"pct_zona_alvo": 92, "principais_desvios": ["km 6–9 em Z5"]},
  "o_que_funcionou": ["pacing σ 1,2s/km", "aquecimento na zona certa"],
  "corrigir_prox_vez": ["gel aos 40min", "teto de FC 175 até o km 16"],
  "contexto_relevante": ["umidade 100% explica ½ do drift"],
  "confianca": "alta | média | baixa"
}
```

O card na UI renderiza `headline` + veredito (✅⚠️❌) + listas; `execucao_vs_intencao` alimenta o gráfico; `confianca` vira um sinal visual discreto.

### 9.3 Divisão de trabalho Python vs LLM

- **Python calcula (determinístico, auditável)**: classificação split-a-split por zona VDOT, % de tempo por zona de FC (config RUNNING), % tempo na zona alvo, drift cardíaco, fade de cadência, decoupling FC/pace, splits 1ª vs 2ª metade, relevo por split, comparativos com sessões anteriores.
- **LLM recebe e devolve**: números prontos + contexto (clima, sono, HRV, RHR, readiness, ACWR) + zonas atuais + PRs + **padrões pessoais** (`km1_rápido`, `fade_15_19`) → JSON do veredito. 
- **System prompt enxuto (~2k tokens)**: só as regras de veredito e o formato — não o SKILL.md inteiro. Números não passam pelo LLM: zero alucinação, menos tokens.

### 9.4 Janela de sync

- Re-puxar sempre os **últimos 3 dias** (Garmin reprocessa sono/carga por até 72h) + atividades novas desde o último sync.
- Teto: **~15 chamadas sequenciais por sync**, com backoff — longe do volume que derrubou a sessão (~40 paralelas).

### 9.5 Régua de potencial máximo

- **Potencial demonstrado** = melhor VDOT de prova máxima (5K 19:23 → VDOT ~53).
- **VDOT corrente** = último teste calibrado (50,2, teste de 10K).
- O painel mostra a **lacuna** com narrativa honesta: "você já demonstrou 53; o teste atual valida 50,2 — o meio é o alvo honesto da próxima prova". **Faixa, nunca número único mágico.**

---

## 10. Prontidão para nuvem e multiusuário — análise honesta

### O que porta fácil (por design do plano)

| Componente | Por que porta |
|---|---|
| Backend FastAPI | Container padrão; deploy é uma tarde de trabalho |
| Frontend Next.js | Vercel ou container; nada de estado local |
| Motor de avaliação | Stateless por requisição (payload → NIM → veredito); escala horizontal sem tocar em nada |
| Registro de tokens/avaliações | Já nasce com `model`, `prompt_version`, `tokens_in/out` — a base de cobrança por uso existe desde a v1 |
| Secrets via env (12-factor) | Já no plano |

### O que exige trabalho real (mas é conhecido e barato SE decidido cedo)

1. **`user_id` no schema desde a Fase 1** (usuário único hardcodado). Retrofit de escopo multiusuário depois é o tipo de refactor que mata projetos — agora custa ~zero.
2. **SQLAlchemy desde a Fase 1**: SQLite→Postgres vira troca de connection string, não reescrita.
3. **Sync como job isolado** (`SyncJob(user_id, janela)`), mesmo rodando in-process na v1 — vira worker de fila (RQ/arq) sem mudar a interface.
4. **Auth**: Supabase Auth/Clerk — ~1 dia.
5. **Cofre de tokens Garmin criptografados** (KMS/age): com terceiros, os dados guardados passam a ser **dados de saúde de outras pessoas** — LGPD manda criptografia em repouso e direito de deletar tudo.
6. **Fluxo "Conectar Garmin" para não-usuários**: o gargalo verdadeiro. O `garminconnect` loga via SSO com email+senha (MFA interativo). No meu caso, isso já existe (tokens do MCP); para um convidado, significa digitar a senha Garmin **no meu site** — funciona entre amigos num beta com disclosure claro, mas é barreira de confiança real e precisa de UX dedicada.

### O que NÃO porta (bloqueio comercial — não de teste controlado)

- **`garminconnect` é a API privada não-oficial do Garmin.** Teste controlado com 5–20 convidados: risco prático baixo. Produto aberto/pago: exposição a ToS + quebra silenciosa (mudança de endpoint derruba todo mundo de uma vez).
- Caminhos oficiais para escalar: **Garmin Health API** (programa de parceiro, review, pago), **Strava API** (OAuth oficial e simples — mas sem sono/HRV/body battery, o que amputaria o painel Saúde), ou upload de FIT.
- **Conclusão**: o gargalo de escala nunca será a infra (FastAPI/Next/NIM escalam por conta própria) — é a **fonte de dados Garmin** e a **confiança nas credenciais**. Por isso a Fase 2.5 existe: validar tudo exceto isso com gente real.

### Decisões de custo zero a travar JÁ na Fase 1

1. ✅ `user_id` (FK) em todas as tabelas — usuário único default
2. ✅ SQLAlchemy (não SQL cru espalhado)
3. ✅ Sync como função de job isolada e chamável
4. ✅ `model`/`prompt_version`/tokens em toda avaliação
5. ✅ Config por env vars, nada hardcodado
