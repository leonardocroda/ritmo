"""Schemas Pydantic para API de domínio Garmin."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SyncJobOut(BaseModel):
    id: int
    status: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error: Optional[str]
    stats: Optional[dict]


class SyncCreatedOut(BaseModel):
    id: int
    status: str


class LatestJobOut(BaseModel):
    job: Optional[SyncJobOut]