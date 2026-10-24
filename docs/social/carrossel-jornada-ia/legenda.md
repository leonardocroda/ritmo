# Carrossel Instagram — "De 1 skill a 302 commits"

Post sobre a jornada de construção da plataforma Ritmo com IA — da skill
de terminal ao app em produção. Formato 4:5 (1080×1350 @2x = 2160×2700),
identidade visual v0.3 (dark Night + lime, Instrument Sans).

## Arquivos

- `slides/slide-01.html` … `slide-10.html` — fonte editável de cada slide
- `png/slide-01.png` … `slide-10.png` — prontos para subir (nesta ordem)
- `capture.py` — renderiza os PNGs (`python capture.py`)
- `check_layout.py` — QA: overflow, fonte e footer (`python check_layout.py`)

Os números citados são reais, contados no repositório (14–24/10/2026):
302 commits, ~13.500 linhas (6.407 Python + 7.115 TS/TSX), 612 funções de
teste, 23 tabelas, 19 endpoints, 232 atividades no primeiro backfill,
US$ 0/mês (Vercel + Render + Neon).

## Legenda (copiar e colar)

Uma skill de terminal virou uma plataforma inteira — o carrossel conta como.

Há poucas semanas eu tinha 4 skills no meu agente de código: elas liam meus dados do Garmin, calibravam minhas zonas de treino e me diziam o que fazer a cada dia. Funcionava tão bem que veio o pensamento: isso é um produto.

Aí, em vez de "faz um app aí", fiz o contrário: escrevi spec antes de qualquer código. Requisitos testáveis, tasks atômicas, commit com gate de teste, verificação independente — quem escreveu não verifica. Esse ciclo repetiu 11 dias seguidos.

O resultado é o Ritmo, minha plataforma pessoal de corrida:

→ sync do Garmin (232 atividades no primeiro backfill)
→ Home que responde "o que eu faço hoje?" em uma frase
→ treinos com splits por zona VDOT, saúde, performance com faixa honesta
→ avaliação com IA sob demanda — Python calcula, o LLM só interpreta
→ 23 tabelas, 19 endpoints, 612 testes, US$ 0/mês de infra
→ doc técnica completa publicada online

E o detalhe que talvez importe mais: tudo isso foi feito nas minhas horas vagas. Nesses 11 dias eu segui na rotina normal — dormi no horário certo, treinei todos os dias e trabalhei (muito) no meu trabalho normal. Nenhuma noite virada. A IA não escreveu só o código comigo: ela devolveu o tempo que um projeto desse costuma engolir.

O que eu aprendi: IA não substitui direção. É o melhor par de programação que eu já tive — mas quem especifica, valida e decide continua sendo você. Você não precisa saber escrever tudo. Precisa saber dirigir.

Salva esse post pro seu próximo projeto. A doc completa tá no link da bio. E me segue: no dia 08/11 eu corro a prova que motivou tudo isso — o próximo capítulo é aqui.

## Hashtags (final da legenda, primeira linha do comentário fixado também serve)

#buildinpublic #vibecoding #ia #desenvolvimentodesoftware #github #running #garmin #corrida #runner #tecnologia

## Comentário fixado sugerido (link clicável, já que a caption não clicla)

A doc técnica completa (API, banco, sync Garmin, frontend, infra — 21 páginas
+ 12 diagramas) e o site público: https://ritmo-docs.onrender.com ·
código no github.com/leonardocroda/ritmo

## Publicação

1. Subir `png/slide-01.png` … `slide-10.png` nesta ordem (carrossel de 10).
2. Colar a legenda + hashtags.
3. Fixar o comentário com o link.
4. Bio: link da doc (ou Linktree) durante a semana do post.
5. Story de repost: sticker de link para o post na capa e no slide 10.

## Editar um slide

1. Editar o HTML correspondente em `slides/`.
2. `python capture.py` — regenera os PNGs.
3. `python check_layout.py` — gate de layout antes de subir.
