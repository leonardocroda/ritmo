"""Application Service do domínio Athlete."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.domain.athlete.domain.entities import Athlete
from app.domain.athlete.ports.repositories import AthleteRepository


@dataclass
class AthleteService:
    repo: AthleteRepository

    def get_or_create(self, user_id: int, display_name: str, email: Optional[str] = None) -> Athlete:
        athlete = self.repo.get_by_user_id(user_id)
        if athlete:
            return athlete
        
        athlete = Athlete(
            id=0,  # Será preenchido pelo repo
            user_id=user_id,
            display_name=display_name,
            email=email,
            created_at=__import__('datetime').datetime.now(),
        )
        return self.repo.save(athlete)

    def get(self, user_id: int) -> Optional[Athlete]:
        return self.repo.get_by_user_id(user_id)

    def update(self, athlete: Athlete) -> Athlete:
        return self.repo.update(athlete)