"""Invariante das pontes strangler (/api/v1 → handlers legados).

Decisão F1 do audit-erros.md: enquanto os domínios novos não têm paridade
com o legado, as rotas /api/v1 re-registram os PRÓPRIOS handlers legados
(uma única implementação). Estes testes travam essa invariante por
introspecção — se alguém trocar um handler de volta por um service de
domínio sem parity test, o teste quebra e força a conversa.
"""

from app.activities import router as activities_router
from app.domain.activity.router import router as v1_activities_router
from app.domain.equipment.bridge_tenis import (
    tenis_analysis_bridge_router,
    tenis_degradation_bridge_router,
)
from app.domain.heart_rate_zones.router import router as v1_hr_zones_router
from app.domain.vdot.router import router as v1_vdot_router
from app.evaluation import router as evaluation_router
from app.profile import router as profile_router
from app.tenis_analysis import router as tenis_analysis_router
from app.tenis_degradation import router as tenis_degradation_router


def _endpoints(router):
    """{(method, path): endpoint_function} do router."""
    out = {}
    for route in router.routes:
        for method in route.methods or set():
            out[(method, route.path)] = route.endpoint
    return out


def test_v1_activities_delegates_to_legacy_handlers():
    legacy = _endpoints(activities_router.router)
    eval_legacy = _endpoints(evaluation_router.router)
    v1 = _endpoints(v1_activities_router)

    assert v1[("GET", "/api/v1/activities")] is legacy[("GET", "/api/activities")]
    assert (
        v1[("GET", "/api/v1/activities/{activity_id}")]
        is legacy[("GET", "/api/activities/{activity_id}")]
    )
    assert (
        v1[("POST", "/api/v1/activities/{activity_id}/evaluate")]
        is eval_legacy[("POST", "/api/activities/{activity_id}/evaluate")]
    )
    assert (
        v1[("GET", "/api/v1/activities/{activity_id}/evaluate/{evaluation_id}")]
        is eval_legacy[("GET", "/api/activities/{activity_id}/evaluate/{evaluation_id}")]
    )


def test_v1_hr_zones_delegates_to_legacy_handlers():
    legacy = _endpoints(profile_router.router)
    v1 = _endpoints(v1_hr_zones_router)

    assert v1[("GET", "/api/v1/heart-rate-zones")] is legacy[("GET", "/api/profile/hr-zones")]
    assert v1[("PUT", "/api/v1/heart-rate-zones")] is legacy[("PUT", "/api/profile/hr-zones")]
    assert (
        v1[("GET", "/api/v1/heart-rate-zones/history")]
        is legacy[("GET", "/api/profile/hr-zones/history")]
    )


def test_v1_vdot_delegates_to_legacy_handler():
    legacy = _endpoints(profile_router.router)
    v1 = _endpoints(v1_vdot_router)

    assert v1[("GET", "/api/v1/vdot")] is legacy[("GET", "/api/profile/pace-zones")]


def test_v1_tenis_bridges_delegate_to_legacy_handlers():
    analysis_legacy = _endpoints(tenis_analysis_router.router)
    degradation_legacy = _endpoints(tenis_degradation_router.router)
    analysis_v1 = _endpoints(tenis_analysis_bridge_router)
    degradation_v1 = _endpoints(tenis_degradation_bridge_router)

    assert analysis_v1[("GET", "/api/v1/tenis/analysis/shoes")] is analysis_legacy[
        ("GET", "/api/tenis/analysis/shoes")
    ]
    assert analysis_v1[("GET", "/api/v1/tenis/analysis/shoes/{shoe_id}")] is analysis_legacy[
        ("GET", "/api/tenis/analysis/shoes/{shoe_id}")
    ]
    assert analysis_v1[("GET", "/api/v1/tenis/analysis/compare")] is analysis_legacy[
        ("GET", "/api/tenis/analysis/compare")
    ]
    assert degradation_v1[("GET", "/api/v1/tenis/degradation/{shoe_id}")] is degradation_legacy[
        ("GET", "/api/tenis/degradation/{shoe_id}")
    ]
