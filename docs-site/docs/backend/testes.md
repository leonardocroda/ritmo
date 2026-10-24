# Backend — Testes

**50 arquivos · 612 testes** contra o **Postgres real** do compose (banco
`ritmo_test`) — nada roda em SQLite, nenhum teste fala com Garmin ou NIM
reais.

## Como roda

```bash
docker compose up -d postgres    # obrigatório
cd backend
uv run pytest
```

Sem o Postgres de pé, a suíte falha **imediatamente** instruindo subir o
banco (probe de conectividade no conftest).

## Harness (`tests/conftest.py` + `helpers.py`)

- `DATABASE_URL` e `TOKEN_ENCRYPTION_KEY` forçadas **antes de qualquer
  import da app** (o conftest vence o `.env`).
- Estado limpo por teste: `drop_all` autouse + o lifespan do TestClient
  recria schema/seeds a cada teste.
- Fixtures `session_client` / `login_client`: TestClient com **sessão
  real** por usuário — é assim que o user-scope é exercitado.
- `fake_garmin.py` + `helpers.py`: `FakeGateway` sobre **payloads reais**
  capturados da API do Garmin (shapes sondados) e builders de dados.

## Cobertura por tema

| Tema | Arquivos |
|---|---|
| Infra/health | `test_health.py` · `test_infra.py` |
| Auth | `test_auth_api.py` · `test_auth_service.py` · `test_auth_models.py` · `test_auth_security.py` · `test_auth_rate_limit.py` · `test_auth_cli.py` |
| Garmin (gateway, mappers, service, upserts, PMC, CLIs, cofre) | `test_garmin_gateway.py` · `test_garmin_mappers.py` · `test_garmin_service.py` · `test_garmin_upserts.py` · `test_garmin_pmc.py` · `test_garmin_login.py` · `test_garmin_import.py` · `test_garmin_tokens_store.py` · `test_garmin_tokens_models.py` · `test_sync_api.py` · `test_sync_config.py` · `test_profile_connection_api.py` |
| Atividades | `test_activities_api.py` · `test_activity_infer.py` · `test_activity_metrics.py` |
| Avaliação IA | `test_evaluation_api.py` · `test_evaluation_service.py` · `test_evaluation_nim.py` · `test_evaluation_payload.py` · `test_evaluation_prompt.py` · `test_evaluation_schemas.py` · `test_evaluation_config.py` |
| Painel Saúde | `test_health_api.py` · `test_health_calc.py` |
| Painel Home | `test_home_api.py` · `test_home_verdict.py` · `test_home_recommendations.py` · `test_home_volume.py` · `test_home_predictions.py` · `test_home_seed.py` · `test_home_service.py` |
| Painel Performance | `test_potential_api.py` · `test_potential_calc.py` |
| VDOT/zonas | `test_vdot_daniels.py` · `test_vdot_zones.py` · `test_vdot_calibration.py` · `test_workouts_config.py` |
| Zonas de FC | `test_hr_zones_api.py` · `test_hr_zones_calc.py` · `test_hr_zones_models.py` · `test_hr_zones_service.py` |
| Isolamento multiusuário | `test_user_isolation.py` (A×B ponta a ponta) |

## Padrões da suíte

- **Literais pinados** nos testes, nunca constantes da implementação — o
  teste é uma segunda leitura do contrato (lição L-001).
- **Garmin 100% falso**: `FakeGateway` + monkeypatch; zero rede.
- **NIM 100% mockada**: `httpx.MockTransport` — nenhum teste paga tokens.
- **Cálculo manual independente** onde o risco é fórmula: a PMC é
  reconferida com `_manual_pmc` escrito no próprio teste.
- Suíte roda no Postgres do compose — o mesmo dialeto de produção
  (índice parcial do lock de sync jobs só existe lá).
