# Pace Zones (VDOT) Specification

## Problem Statement

O app tem a página de perfil com cards para "Zonas de FC" e "Equipamentos", mas não há nenhum lugar para visualizar as zonas de ritmo (VDOT) calculadas pela calibração de Jack Daniels. O arquivo `vdot_zones.json` existe no backend e alimenta os painéis de treino e performance, mas o usuário não consegue consultar essas zonas diretamente no app.

## Goals

- [ ] Criar tabela dedicada `vdot_zone_configs` no banco para persistir zonas VDOT (substitui `vdot_zones.json`)
- [ ] Migrar dado atual do JSON para a tabela (seed/migration one-shot)
- [ ] Atualizar script de calibração (`calibrate_vdot.py`) para gravar no banco em vez do JSON
- [ ] Criar endpoint `/api/profile/pace-zones` que lê do banco (user-scope)
- [ ] Criar página `/pace-zones` no frontend que exibe as zonas de ritmo de forma clara e visual
- [ ] Adicionar card "Zonas de Ritmo" na página `/perfil` linkando para a nova página
- [ ] Incluir botão "Recalibrar" que orienta o usuário a rodar a calibração via CLI

## Out of Scope

| Feature | Reason |
|---------|--------|
| Calibração web interativa (entrevista no browser) | Requer novo fluxo complexo; o CLI atual funciona bem |
| Histórico de calibrações passadas (múltiplas linhas) | MVP: uma linha vigente por usuário; histórico é feature futura |
| Edição manual de zonas individuais | Zonas são derivadas do VDOT; editar manualmente quebra a consistência |
| Atualizar painéis `activities` e `potential` para ler do banco | Eles continuam lendo do JSON por enquanto (compatibilidade) |

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
|-----------------------|----------------|-----------|------------|
| URL da página | `/pace-zones` (inglês nas rotas) | Consistência com decisão do usuário | y |
| Conteúdo exibido | Tudo do `vdot_zones.json`: VDOT, 5 zonas, equivalências, fonte/teste | Usuário pediu completo | y |
| Botão recalibrar | Exibe modal com comando CLI (`python calibrate_vdot.py`) | Não dá pra abrir terminal do browser; instrução clara resolve | y |
| Auth | Mesma proteção das outras páginas do app (cookie de sessão) | Padrão existente no app | y |
| Fonte de dados | Nova tabela `vdot_zone_configs` (user-scope, 1 linha vigente) | Decisão do usuário: tabela dedicada | y |
| Migração JSON → DB | Script one-shot na migration (Alembic `data` migration) | Dado único existente; não precisa CLI separado | y |
| Script calibração | Atualiza tabela + mantém JSON para compatibilidade painéis | `activities`/`potential` ainda leem JSON | y |
| Tratamento tabela vazia | 500 "zonas VDOT não configuradas" (consistente com painéis) | Mesmo contrato de erro | y |

**Open questions:** none - all resolved or logged above.

---

## User Stories

### P1: Visualizar zonas de ritmo (VDOT) ⭐ MVP

**User Story**: Como corredor, quero ver minhas zonas de ritmo (VDOT) no app para saber em que pace correr cada tipo de treino (easy, maratona, limiar, intervalado, repetição).

**Why P1**: É a funcionalidade central - sem ela, o usuário não tem acesso às zonas que já foram calculadas.

**Acceptance Criteria**:

1. WHEN o usuário acessa `/pace-zones` autenticado ENTÃO o sistema SHALL exibir o VDOT atual, a fonte do teste e a data do teste (lidos do banco)
2. WHEN o usuário acessa `/pace-zones` ENTÃO o sistema SHALL exibir as 5 zonas (Easy, Maratona, Limiar, Intervalado, Repetição) com pace range/pace, descrição e cor
3. WHEN o usuário acessa `/pace-zones` ENTÃO o sistema SHALL exibir as equivalências de prova (5K, 10K, Meia Maratona, Maratona) com pace
4. IF a tabela `vdot_zone_configs` não tem linha para o usuário ENTÃO o sistema SHALL retornar 500 com mensagem "zonas VDOT não configuradas"
5. The system SHALL proteger a rota com autenticação (redirect para `/login?next=/pace-zones` se não logado)

**Independent Test**: Acessar `/pace-zones` logado e ver todas as zonas + VDOT + equivalências renderizadas; acessar deslogado e ser redirecionado para login.

---

### P1: Card "Zonas de Ritmo" no perfil

**User Story**: Como usuário, quero um card "Zonas de Ritmo" na página de perfil que me leve para a página de zonas VDOT, assim como existem cards para Zonas de FC e Equipamentos.

**Why P1**: Descobribilidade - o usuário precisa saber que as zonas de ritmo existem e onde encontrá-las.

**Acceptance Criteria**:

1. WHEN o usuário acessa `/perfil` ENTÃO o sistema SHALL exibir um card "Zonas de Ritmo" na lista de seções (após Zonas de FC e Equipamentos)
2. WHEN o usuário clica no card "Zonas de Ritmo" ENTÃO o sistema SHALL navegar para `/pace-zones`
3. The system SHALL usar o mesmo estilo visual dos cards existentes (ícone, título, subtítulo, seta)

**Independent Test**: Acessar `/perfil` e ver o terceiro card "Zonas de Ritmo" com link funcionando.

---

### P2: Botão recalibrar com instrução CLI

**User Story**: Como usuário, quero um botão "Recalibrar" na página de zonas de ritmo que me mostre como rodar a calibração via CLI, para poder atualizar meu VDOT quando fizer um novo teste.

**Why P2**: Permite manter as zonas atualizadas sem sair do app (pelo menos com a instrução).

**Acceptance Criteria**:

1. WHEN o usuário está em `/pace-zones` ENTÃO o sistema SHALL exibir um botão "Recalibrar"
2. WHEN o usuário clica em "Recalibrar" ENTÃO o sistema SHALL abrir um modal com o comando `python calibrate_vdot.py` e explicação breve
3. The system SHALL usar o mesmo padrão visual de modais/botões do app

**Independent Test**: Estar em `/pace-zones`, clicar "Recalibrar", ver modal com comando e fechar.

---

## Edge Cases

1. IF tabela `vdot_zone_configs` sem linha para o usuário THEN API retorna 500 "zonas VDOT não configuradas"
2. IF usuário não autenticado THEN redirect para `/login?next=/pace-zones` (padrão `apiFetch`)
3. IF JSON legacy ausente mas tabela populada THEN painéis `activities`/`potential` falham (fora do escopo — compatibilidade mantida com JSON)
4. IF calibração roda e falha escrita no banco THEN rollback + erro 500 (transação única)

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
|----------------|-------|-------|--------|
| PZ-01 | P1: Visualizar zonas | In Tasks | Implementing |
| PZ-02 | P1: Visualizar zonas | In Tasks | Implementing |
| PZ-03 | P1: Visualizar zonas | Design | Pending |
| PZ-04 | P1: Visualizar zonas (error) | Design | Pending |
| PZ-05 | P1: Visualizar zonas (auth) | Design | Pending |
| PZ-06 | P1: Card no perfil | Design | Pending |
| PZ-07 | P1: Card no perfil | Design | Pending |
| PZ-08 | P1: Card no perfil | Design | Pending |
| PZ-09 | P2: Botão recalibrar | Design | Pending |
| PZ-10 | P2: Botão recalibrar | Design | Pending |
| PZ-11 | P2: Botão recalibrar | Design | Pending |

**ID format:** `PZ-[NUMBER]`

**Coverage:** 11 total, 11 mapped to stories, 0 unmapped

---

## Success Criteria

- [ ] Tabela `vdot_zone_configs` criada no banco com migração
- [ ] Dado do `vdot_zones.json` migrado para a tabela (seed na migration)
- [ ] Script `calibrate_vdot.py` atualizado para gravar no banco (e manter JSON)
- [ ] Usuário autenticado acessa `/pace-zones` e vê VDOT, 5 zonas, equivalências, fonte/teste (do banco)
- [ ] Usuário não autenticado é redirecionado para login
- [ ] Card "Zonas de Ritmo" aparece no perfil e navega corretamente
- [ ] Botão "Recalibrar" abre modal com instrução CLI
- [ ] Erro 500 consistente quando tabela sem linha para o usuário