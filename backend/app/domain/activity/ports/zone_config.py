"""Port para provedor de configuração de zonas."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.domain.activity.domain.value_objects import ZoneConfigVO


@runtime_checkable
class ZoneConfigProvider(Protocol):
    """Provedor de configuração de zonas VDOT/FC para um usuário."""

    def get_for_user(self, user_id: int) -> ZoneConfigVO: ...
    def invalidate_cache(self, user_id: int) -> None: ...