# hr-zones Specification

## Problem Statement

As zonas de frequência cardíaca do Ritmo hoje não existem como conceito próprio: o app tem
zonas de **pace** VDOT (arquivo `vdot_zones.json`, usadas na coloração de voltas e no tipo
inferido) e um único número `LTHR_BPM` no env (177) que alimenta o payload da avaliação IA —
o mesmo valor para qualquer usuário. Para o MVP de convidados (Fase 1.5), cada corredor
precisa das **suas** zonas de FC: derivadas de `fclthr`, `fcmax` e `fcrest`, por um método
escolhido (LTHR%, reserva cardíaca/Karvonen, FC máx%), com **histórico** de valores e
configurações — um treino antigo é lido com as zonas vigentes na data dele (padrão
Strava/Garmin: mudança vale dali em diante). Valores podem vir do Garmin automaticamente,
mas a edição manual vence e nunca é sobrescrita pelo sync. Decisão do usuário (20/10/2026):
esta feature cobre **só o eixo de FC**; as zonas VDOT de pace seguem no arquivo (plano
per-user da AD-015 fica adiado).

## Goals

- [x] fcmax, fcrest e fclthr por usuário no banco, com histórico effective-dated (append-only)
- [x] Config de zonas por usuário: método (`lthr` | `fcr` | `fcmax`) + percentuais editáveis
      por zona com defaults por método e guardrails
- [x] Zonas em bpm derivadas na leitura, vigentes na data consultada (treino antigo →
      zonas da época)
- [x] Tela `/perfil` (nasce aqui) com a tela de zonas: valores, método, percentuais,
      zonas resultantes e histórico
- [x] Avaliação IA: `lthr_bpm` do perfil do usuário (fallback: env) + bloco de tempo por
      zona de FC
- [x] Sync traz as três métricas — `fcmax` e `fclthr` auto-detectados do Garmin, `fcrest`
      derivada da série sincronizada — sem nunca sobrescrever edição manual

## Out of Scope

| Feature | Reason |
| --- | --- |
| Zonas VDOT de pace por usuário (AD-015) | Decisão do usuário (20/10): eixo de FC é novo e paralelo; pace segue no `vdot_zones.json` — adiado |
| Reclassificação retroativa de treinos | Decisão do usuário: vigente-na-data (padrão Strava); o passado não é reescrito |
| Zonas por esporte (Garmin per-sport) | App é de corrida; um conjunto de zonas basta |
| Entrevista de calibração self-service no app | Fase 2 (AD-015 segue de pé para a FC) |
| Resto do `/perfil` (nome, troca de senha, status Garmin) | Feature `user-profile` (5ª da Fase 1.5); aqui o `/perfil` nasce só com a tela de zonas |
| Zonas de FC em novos painéis (Saúde, gráfico do detalhe) | Consumo inicial: tela de zonas + payload da avaliação; painéis pedem spec própria com uso real |
| Delete/correção de entradas do histórico | Append-only; corrigir = valor novo (auditoria preservada) |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Nome da feature | `hr-zones` (renomeia `zones-db` no roadmap) | Decisão do usuário (20/10): escopo mudou — zonas de FC com histórico | y |
| Zonas VDOT de pace | Seguem no arquivo; per-user adiado | Decisão do usuário: eixo de FC é paralelo ao eixo de pace | y |
| Retroatividade | Vigente-na-data: métricas e configs com `valid_from`; leitura em D usa a vigente em D | Decisão do usuário; padrão Strava (mudança vale dali em diante) | y |
| Percentuais | Defaults por método + editáveis por zona com guardrails | Decisão do usuário; padrão Garmin/Strava (defaults alocados, edição livre validada) | y |
| Manual vs Garmin | Manual vence: sync só cria linha se o valor mudar E a vigente não for `source=manual` | Decisão do usuário: editar independe do Garmin | y |
| Tela | `/perfil` nasce nesta feature (shell + zonas); user-profile expande depois | Decisão do usuário: backend + tela agora | y |
| Defaults por método | lthr: 65/80/89/95/100 (tabela do usuário); fcr: 50/60/70/80/90; fcmax: 50/60/70/80/90 | Tabela LTHR proposta pelo usuário (variação legítima de 5 zonas; Friel usa 7); fcr/fcmax seguem Karvonen/Polar-ACSM |
| Semântica de zona | `low ≤ FC < high` (lower inclusivo, upper exclusivo); Z5 do LTHR é aberta (`> low`); fcr/fcmax fecham em 100% (= fcmax) | Sem gaps nem sobreposição; guardrail Strava de não-sobreposição fica trivial |
| Arredondamento | bpm inteiro (`round`); percentuais em pontos inteiros | Régua de leitura simples; valores ≥100 bpm + ≥1pp ⇒ sem colapso de zona | y |
| Limites de valor | fcmax 100–230 (teto Strava), fcrest 30–110, fclthr 100–220; incoerências (fcrest ≥ fcmax, fclthr ≥ fcmax) → 422 | Sanidade mínima sem travar valores reais | y |
| API do Garmin para os valores | `garminconnect` expõe FC máx/LTHR/FC repouso auto-detectados — **spike na implementação**; se LTHR indisponível, `fclthr` fica só manual | Não fabricar endpoint: `get_user_settings` e `get_lactate_threshold` estão verificados na lib 0.3.2 instalada; a chave exata do `maxHeartRate` e a presença do LTHR detectado se confirmam no spike runtime; o fallback do env cobre o payload até o sync popular | n (spike) |
| Seed do usuário 1 | **Nenhuma métrica é seedada** — só a config de zonas (lthr + defaults); métricas vêm do primeiro sync ou de edição manual; o payload cai no fallback do env (`LTHR_BPM`) enquanto `fclthr` não existir | Decisão do usuário (20/10): o sync é a fonte de todas as infos, inclusive LTHR — seed manual bloquearia o auto-update para sempre (manual-wins) | y |
| `fcrest` no sync | Auto-atualizada a cada sync: mínimo dos últimos 7 dias da série `rhr` sincronizada, `source=garmin`, update-if-changed (manual-wins) | Decisão do usuário: todas as infos vêm do sync; a evolução da fcrest é o histórico que o spec pede | y |
| `LTHR_BPM` env | Vira **fallback** do payload de avaliação quando não há métrica do usuário | Transição suave; convidado sem valores ainda avalia (números menos pessoais, mas honestos) | y |
| Endpoints | `GET/PUT /api/profile/hr-zones` + `GET /api/profile/hr-zones/history`; PUT é a única escrita (valores e/ou método e/ou bounds) | Contrato pequeno e único; cada mudança vira linha(s) nova(s) | y |
| Escrita idempotente | PUT/sync com valor igual ao vigente → sem linha nova (200/204) | Histórico conta mudanças reais, não ruído | y |

**Open questions:** none — all resolved or logged above (required before the spec is confirmed).

---

## User Stories

### P1: Métricas fisiológicas com histórico ⭐ MVP

**User Story**: As a corredor, I want que minha FC máxima, FC de repouso e LTHR fiquem
salvos por usuário com histórico de mudanças so que o app use meus números reais (não um
padrão de fábrica) e eu veja a evolução.

**Why P1**: Sem os valores não há zonas; sem histórico não há leitura vigente-na-data.

**Acceptance Criteria**:

1. WHEN `GET /api/profile/hr-zones` chega com sessão válida THEN o sistema SHALL devolver
   os valores vigentes de `fcmax`, `fcrest` e `fclthr` — cada um `{value, source, valid_from}`
   ou null quando nunca configurado  <!-- event-driven -->
2. WHEN `PUT /api/profile/hr-zones` recebe um novo valor de métrica THEN o sistema SHALL
   criar linha nova com `source=manual` e `valid_from` = hoje, preservando as anteriores no
   histórico (append-only, nunca sobrescreve)  <!-- event-driven -->
3. IF o valor enviado é igual ao vigente THEN o sistema SHALL responder sucesso sem criar
   linha nova (idempotente)  <!-- unwanted-behavior -->
4. IF o valor está fora dos limites (fcmax 100–230, fcrest 30–110, fclthr 100–220) ou é
   incoerente (fcrest ≥ fcmax, fclthr ≥ fcmax) THEN o sistema SHALL responder 422
   apontando o campo e o motivo  <!-- unwanted-behavior -->
5. WHEN o sync executa THEN o sistema SHALL atualizar as três métricas do usuário a partir
   das fontes automáticas — `fcmax` e `fclthr` da API do Garmin (auto-detectados; valor
   ausente → pula a métrica) e `fcrest` derivada do mínimo dos últimos 7 dias da série
   `rhr` sincronizada — criando linha `source=garmin` quando o valor difere do vigente  <!-- event-driven -->
6. IF a linha vigente tem `source=manual` THEN o sync SHALL não criar linha nova para
   aquela métrica (a edição manual nunca é sobrescrita pelo Garmin)  <!-- unwanted-behavior -->
7. WHEN o banco inicializa com o usuário 1 sem config THEN o sistema SHALL semear apenas
   a config de zonas (método lthr + defaults); nenhuma métrica é seedada — vêm do sync
   (HRZ-05) ou de edição manual, e o payload usa o fallback do env enquanto `fclthr` não
   existir  <!-- event-driven -->

**Independent Test**: PUT fclthr=185 → GET devolve 185/hoje; PUT 185 de novo → mesma
resposta, zero linhas novas no histórico; PUT 400 → 422; sync com LTHR auto-detectado
diferente → linha `source=garmin`; PUT manual de novo → próximo sync não sobrescreve.

---

### P1: Config de método e percentuais + zonas derivadas ⭐ MVP

**User Story**: As a corredor, I want escolher o método das minhas zonas (LTHR%, reserva
cardíaca, FC máx%) e ajustar os percentuais por zona so que as zonas reflitam meu método
de treino — e um treino antigo seja lido com as zonas da época.

**Why P1**: É o coração da feature — zonas são configuração, não número fixo de fábrica.

**Acceptance Criteria**:

8. WHEN o método é alterado THEN o sistema SHALL criar config nova com os defaults do
   método (lthr: 65/80/89/95/100; fcr: 50/60/70/80/90; fcmax: 50/60/70/80/90), sem tocar
   nas métricas  <!-- event-driven -->
9. WHEN percentuais são editados THEN o sistema SHALL criar config nova com os bounds
   custom; IF os bounds são inválidos (≠5 zonas, cadeia não ascendente `z1.low < z1.high =
   z2.low < … < z5.low`, zona <1 ponto, `z1.low ≤ 0`, upper em Z5 do LTHR) THEN o sistema
   SHALL responder 422 com o primeiro ponto inválido  <!-- complex -->
10. WHILE as métricas exigidas pelo método existem THEN o sistema SHALL derivar as zonas
    em bpm na leitura (lthr: `round(pct × fclthr)`; fcr: `fcrest + round(pct × (fcmax −
    fcrest))`; fcmax: `round(pct × fcmax)`), com `low ≤ FC < high` e Z5 do LTHR aberta  <!-- state-driven -->
11. IF uma métrica exigida pelo método não existe (ex.: fcr sem fcrest) THEN o sistema
    SHALL devolver zonas null (estado vazio honesto que orienta configurar, não erro)  <!-- unwanted-behavior -->
12. WHEN uma leitura em data D resolve as zonas (tela ou payload) THEN o sistema SHALL
    usar a métrica e a config vigentes em D — treino antigo é lido com as zonas da época  <!-- event-driven -->

**Independent Test**: PUT método=lthr com fclthr 177 → zonas [115, 141, 156, 168, 177+];
PUT método=fcr sem fcrest → zonas null com orientação; PUT bounds 64/79/88/94/99 no lthr →
zonas recalculadas; treino de 30 dias atrás → zonas da config daquela data.

---

### P1: Tela de zonas no `/perfil` ⭐ MVP

**User Story**: As a usuário autenticado, I want uma tela de zonas dentro do `/perfil`
com meus valores, método, percentuais, zonas resultantes e histórico so que eu configure
e acompanhe minhas zonas sem depender do operador.

**Why P1**: "Mudar independentemente do Garmin" exige tela própria; é a face da feature.

**Acceptance Criteria**:

13. WHEN um usuário autenticado abre `/perfil` THEN o sistema SHALL exibir os valores com
    badge de fonte (Garmin/Manual) e vigência, o método selecionado, os percentuais e as
    zonas resultantes em bpm (padrão de clareza AD-009: cabeçalho forte, subtítulo "o que
    é / por que importa")  <!-- event-driven -->
14. WHEN o usuário edita valor, método ou percentual THEN o client SHALL chamar o PUT e
    re-renderizar as zonas resultantes; IF a resposta é 422 THEN o client SHALL exibir o
    erro inline por campo, em PT-BR  <!-- complex -->
15. WHEN o usuário consulta o histórico THEN a tela SHALL listar as mudanças de métricas
    e configs, mais recente primeiro, com data e fonte  <!-- event-driven -->
16. IF um usuário sem sessão abre `/perfil` THEN o sistema SHALL aterrissar em `/login`
    (proteção existente das telas)  <!-- unwanted-behavior -->

**Independent Test**: no celular (390px), editar fclthr de 177 para 185 → zonas em bpm
mudam na hora com badge "Manual"; trocar para fcr → zonas recalculadas com defaults;
histórico mostra as duas mudanças com datas.

---

### P1: Consumo na avaliação IA ⭐ MVP

**User Story**: As a usuário, I want que a avaliação IA do meu treino use meu LTHR e meu
tempo por zona de FC so that o veredito reflita minhas zonas, não as de outro usuário.

**Why P1**: Era a motivação original da AD-015 — dois corredores não compartilham limiar.

**Acceptance Criteria**:

17. WHEN o payload da avaliação é montado THEN `lthr_bpm` SHALL vir da métrica `fclthr`
    do usuário vigente na data do treino; IF a métrica não existe THEN `lthr_bpm` SHALL
    usar o fallback do env (`LTHR_BPM`)  <!-- complex -->
18. WHEN o treino tem FC nas voltas THEN o payload SHALL incluir o tempo por zona de FC
    (segundos e % por zona, contando só voltas com FC e duração), com as zonas vigentes na
    data do treino  <!-- event-driven -->
19. IF nenhuma volta tem FC THEN o payload SHALL omitir o bloco de zonas de FC (nenhum
    número inventado — mesma postura do bloco de pace)  <!-- unwanted-behavior -->

**Independent Test**: avaliar um treino com FC → payload traz `lthr_bpm` do perfil e
`tempo por zona de FC` coerente com os splits; mesmo treino sem FC → bloco ausente.

---

## Edge Cases

- IF `fclthr ≥ fcmax` é enviado THEN 422 "limiar acima da FC máxima" (incoerência fisiológica)
- IF o sync traz o MESMO valor do vigente THEN nenhuma linha nova (idempotente, mesmo
  padrão do upsert de saúde)
- WHEN o mínimo-7d da `fcrest` muda entre syncs THEN a história registra a mudança — é a
  evolução do valor que o usuário pediu (dado, não ruído; fcmax/LTHR mudam raramente,
  fcrest acompanha a forma física)
- IF o usuário muda só o método THEN as métricas ficam intactas; IF muda só um percentual
  THEN o método fica (config nova herda o resto)
- IF a config vigente era manual e o sync muda um valor source=garmin THEN as zonas do
  método que não dependem daquele valor seguem válidas (métrica e config são séries
  independentes)
- WHEN as zonas mudam THEN treinos passados NÃO são reclassificados (vigente-na-data —
  decisão do usuário; a mudança vale dali em diante)
- IF o método é lthr e a FC de um split excede a Z4 THEN cai na Z5 aberta (> 100% do LTHR,
  sem teto inventado)
- IF PUT altera valor E método na mesma chamada THEN ambas as linhas são criadas com o
  mesmo `valid_from` (uma época coerente)

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| HRZ-01 | P1: Métricas com histórico | Design | ✅ Implemented |
| HRZ-02 | P1: Métricas com histórico | Design | ✅ Implemented |
| HRZ-03 | P1: Métricas com histórico | Design | ✅ Implemented |
| HRZ-04 | P1: Métricas com histórico | Design | ✅ Implemented |
| HRZ-05 | P1: Métricas com histórico | Design | Pending |
| HRZ-06 | P1: Métricas com histórico | Design | ✅ Implemented |
| HRZ-07 | P1: Métricas com histórico | Design | ✅ Implemented |
| HRZ-08 | P1: Config de método e zonas | Design | ✅ Implemented |
| HRZ-09 | P1: Config de método e zonas | Design | ✅ Implemented |
| HRZ-10 | P1: Config de método e zonas | Design | ✅ Implemented |
| HRZ-11 | P1: Config de método e zonas | Design | ✅ Implemented |
| HRZ-12 | P1: Config de método e zonas | Design | ✅ Implemented |
| HRZ-13 | P1: Tela de zonas no /perfil | Design | Pending |
| HRZ-14 | P1: Tela de zonas no /perfil | Design | Pending |
| HRZ-15 | P1: Tela de zonas no /perfil | Design | ✅ Implemented |
| HRZ-16 | P1: Tela de zonas no /perfil | Design | Pending |
| HRZ-17 | P1: Consumo na avaliação IA | Design | Pending |
| HRZ-18 | P1: Consumo na avaliação IA | Design | Pending |
| HRZ-19 | P1: Consumo na avaliação IA | Design | Pending |

**Coverage:** 19 total, 0 mapped to tasks, 19 unmapped ⚠️

---

## Success Criteria

- [ ] Usuário 1 roda o sync pós-feature: fclthr e fcmax chegam do Garmin (auto-detectados),
      fcrest do mínimo-7d — e as zonas LTHR aparecem na tela `/perfil` no celular (390px),
      editáveis (percentuais mudam as zonas na hora)
- [ ] Até o primeiro sync popular `fclthr`, o payload da avaliação usa o fallback do env
      (177); depois, o LTHR do perfil
- [ ] Editar um valor manualmente e rodar o sync: o valor manual permanece (badge
      "Manual"), o histórico registra só mudanças reais
- [ ] Avaliação IA de um treino com FC traz `lthr_bpm` do perfil e tempo por zona de FC;
      treino sem FC omite o bloco
- [ ] Treino de um mês atrás é lido com as zonas vigentes naquela data (effective-dating)
- [ ] Suite completa verde no Postgres do compose (backend) + build do frontend sem erros
- [ ] `GET /api/profile/hr-zones` sem sessão → 401 (padrão user-scope)
