# Design: Backend Decoupling — Pragmatic Hexagonal Architecture

## Overview

This design adopts a **pragmatic hexagonal architecture** — three layers with dependency inversion at the boundaries, using FastAPI's native `Depends` for DI and Python `Protocol` for ports. No external DI container, no ceremony.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PRESENTATION LAYER                                │
│  ┌─────────────────────────────┐  ┌─────────────────────────────────────┐  │
│  │  DOMAIN API ROUTERS         │  │  BFF COMPOSITION ROUTERS            │  │
│  │  /api/v1/activities         │  │  /api/v1/bff/home/today             │  │
│  │  /api/v1/health/sleep       │  │  /api/v1/bff/health/summary         │  │
│  │  /api/v1/training-load/pmc  │  │  /api/v1/bff/performance            │  │
│  │  /api/v1/performance/vdot   │  │  /api/v1/bff/activities             │  │
│  │  /api/v1/shoes              │  │  /api/v1/bff/profile/zones          │  │
│  └──────────────┬──────────────┘  └──────────────────┬──────────────────┘  │
└─────────────────┼───────────────────────────────────┼───────────────────────┘
                  │                                   │
                  ▼                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        APPLICATION / USE CASES                              │
│  app/domain/{context}/service.py — orchestrate, no HTTP/DB deps            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐  │
│  │ ActivitySvc │ │ HealthSvc   │ │ PerfSvc     │ │ ShoesSvc            │  │
│  │ TrainingSvc │ │ EvalSvc     │ │ ProfileSvc  │ │ DegradationSvc      │  │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └─────────┬──────────┘  │
└─────────┼───────────────┼───────────────┼────────────────┼────────────────┘
          │               │               │                │
    ┌─────┴─────┐   ┌─────┴─────┐   ┌─────┴─────┐   ┌─────┴─────┐
    ▼           ▼   ▼           ▼   ▼           ▼   ▼           ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│Activity│ │ Sleep  │ │ PMCCalc│ │ VDOT   │ │Degrad- │ │ Shoe   │
│Consist │ │Repo    │ │        │ │Service │ │Signal  │ │Analysis│
└────────┘ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘
    │           │        │        │        │        │
    ▼           ▼        ▼        ▼        ▼        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DOMAIN CORE (zero deps)                           │
│  Entities, Value Objects, Domain Services, Domain Events                   │
│  app/domain/{context}/domain/                                               │
└─────────────────────────────────────────────────────────────────────────────┘
          │               │        │        │        │        │
          ▼               ▼        ▼        ▼        ▼        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            OUTBOUND PORTS (Protocols)                       │
│  app/domain/{context}/ports/                                                │
│  ┌──────────────────┐ ┌──────────────────┐ ┌────────────────────────────┐  │
│  │ ActivityRepo     │ │ GarminClient     │ │ AIClient (NIM)             │  │
│  │ SplitRepo        │ │ StravaClient     │ │ ZoneConfigProvider         │  │
│  │ ShoeRepo         │ │ TokenStore       │ │ NotificationSender         │  │
│  └──────────────────┘ └──────────────────┘ └────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
          │               │        │        │        │        │
          ▼               ▼        ▼        ▼        ▼        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         OUTBOUND ADAPTERS (impl)                            │
│  app/domain/{context}/adapters/                                             │
│  ┌──────────────────┐ ┌──────────────────┐ ┌────────────────────────────┐  │
│  │ SQLAlchemyRepo   │ │ GarminAPIClient  │ │ NIMClient                  │  │
│  │ SQLAlchemySplit  │ │ StravaAPIClient  │ │ DBZoneConfigProvider       │  │
│  │ SQLAlchemyShoe   │ │ TokenStoreDB     │ │ EmailNotifier              │  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Module Structure

```
app/
├── domain/
│   ├── activities/
│   │   ├── domain/
│   │   │   ├── entities.py          # Activity, Split, Lap, RunningDynamics
│   │   │   ├── value_objects.py     # Pace, HeartRate, Cadence, ZoneKey
│   │   │   ├── services.py          # ConsistencyCalculator, ZoneClassifier
│   │   │   └── events.py            # ActivityImported, ActivityEvaluated
│   │   ├── ports/
│   │   │   ├── repositories.py      # ActivityRepository, SplitRepository
│   │   │   └── zone_config.py       # ZoneConfigProvider
│   │   ├── adapters/
│   │   │   ├── sqlalchemy_repo.py   # SQLAlchemyActivityRepository
│   │   │   ├── sqlalchemy_split.py  # SQLAlchemySplitRepository
│   │   │   └── db_zone_config.py    # DBZoneConfigProvider
│   │   ├── schemas.py               # Pydantic DTOs for API (request/response)
│   │   ├── service.py               # ActivityService (use cases)
│   │   ├── dependencies.py          # FastAPI Depends providers
│   │   └── router.py                # Domain API router
│   │
│   ├── training_load/
│   │   ├── domain/
│   │   │   ├── entities.py          # PMCCurve, PMCDay, ATLCTL, ACWR
│   │   │   ├── services.py          # PMCCalculator, VolumeCalculator
│   │   │   └── value_objects.py     # TrainingLoad, IntensityFactor
│   │   ├── ports/
│   │   │   └── repositories.py      # ActivityRepository (read-only)
│   │   ├── adapters/
│   │   │   └── sqlalchemy_repo.py
│   │   ├── schemas.py
│   │   ├── service.py               # TrainingLoadService
│   │   ├── dependencies.py
│   │   └── router.py
│   │
│   ├── health/
│   │   ├── domain/
│   │   │   ├── entities.py          # SleepNight, HRVReading, RHRReading
│   │   │   ├── value_objects.py     # HRVStatus, SleepScore, StressLevel
│   │   │   ├── services.py          # HRVBaseline, DoseResponseCalculator
│   │   │   └── events.py            # HealthDataSynced
│   │   ├── ports/
│   │   │   └── repositories.py      # HealthRepository
│   │   ├── adapters/
│   │   │   └── sqlalchemy_repo.py
│   │   ├── schemas.py
│   │   ├── service.py               # HealthService
│   │   ├── dependencies.py
│   │   └── router.py
│   │
│   ├── performance/
│   │   ├── domain/
│   │   │   ├── entities.py          # VDOTProfile, Prediction, DecayPoint
│   │   │   ├── value_objects.py     # VDOT, RaceTime, EventDistance
│   │   │   ├── services.py          # VDOTCalculator, DanielsTables
│   │   │   └── events.py            # VDOTUpdated
│   │   ├── ports/
│   │   │   └── repositories.py      # PerformanceRepository
│   │   ├── adapters/
│   │   │   └── sqlalchemy_repo.py
│   │   ├── schemas.py
│   │   ├── service.py               # PerformanceService
│   │   ├── dependencies.py
│   │   └── router.py
│   │
│   ├── shoes/
│   │   ├── domain/
│   │   │   ├── entities.py          # Shoe, ShoeRun, DegradationSignal
│   │   │   ├── value_objects.py     # ShoeStatus, KM, RunTypeBand
│   │   │   ├── services.py          # DegradationAnalyzer, ComparisonEngine
│   │   │   └── events.py            # ShoeRetired, SignalDetected
│   │   ├── ports/
│   │   │   └── repositories.py      # ShoeRepository
│   │   ├── adapters/
│   │   │   └── sqlalchemy_repo.py
│   │   ├── schemas.py
│   │   ├── service.py               # ShoesService, DegradationService
│   │   ├── dependencies.py
│   │   └── router.py
│   │
│   ├── evaluation/
│   │   ├── domain/
│   │   │   ├── entities.py          # EvaluationJob, Verdict, Intent
│   │   │   ├── value_objects.py     # VerdictType, Confidence, PromptVersion
│   │   │   ├── services.py          # PromptBuilder, VerdictParser
│   │   │   └── events.py            # EvaluationCompleted
│   │   ├── ports/
│   │   │   ├── repositories.py      # EvaluationRepository
│   │   │   └── ai_client.py         # AIClient
│   │   ├── adapters/
│   │   │   ├── sqlalchemy_repo.py
│   │   │   └── nim_client.py
│   │   ├── schemas.py
│   │   ├── service.py               # EvaluationService
│   │   ├── dependencies.py
│   │   └── router.py
│   │
│   ├── profile/
│   │   ├── domain/
│   │   │   ├── entities.py          # HRZoneConfig, PaceZoneConfig, UserSettings
│   │   │   ├── value_objects.py     # HRZoneMethod, HRZoneBounds, VDOTZone
│   │   │   ├── services.py          # HRZoneCalculator, VDOTZoneBuilder
│   │   │   └── events.py            # ZonesUpdated
│   │   ├── ports/
│   │   │   └── repositories.py      # ProfileRepository
│   │   ├── adapters/
│   │   │   └── sqlalchemy_repo.py
│   │   ├── schemas.py
│   │   ├── service.py               # ProfileService
│   │   ├── dependencies.py
│   │   └── router.py
│   │
│   └── garmin/                      # Integration domain (not screen-coupled)
│       ├── domain/
│       │   ├── entities.py          # GarminActivity, GarminSleep, GarminHRV
│       │   ├── value_objects.py     # GarminActivityType, SyncStatus
│       │   └── services.py          # ActivityMapper, SleepMapper
│       ├── ports/
│       │   ├── client.py            # GarminClient
│       │   └── token_store.py       # TokenStore
│       ├── adapters/
│       │   ├── garmin_client.py
│       │   └── token_store_db.py
│       ├── schemas.py
│       ├── service.py               # SyncService, ImportService
│       ├── dependencies.py
│       └── router.py                # Sync endpoints (unchanged)
│
├── bff/                             # BFF Composition Layer (Backend for Frontend)
│   ├── home/
│   │   ├── schemas.py               # HomeTodayOut (BFF-specific payload)
│   │   ├── service.py               # HomeBFFService (composes domain services)
│   │   ├── dependencies.py
│   │   └── router.py                # GET /api/v1/bff/home/today
│   │
│   ├── health/
│   │   ├── schemas.py               # HealthSummaryOut
│   │   ├── service.py               # HealthBFFService
│   │   ├── dependencies.py
│   │   └── router.py                # GET /api/v1/bff/health/summary
│   │
│   ├── performance/
│   │   ├── schemas.py               # PerformanceBFFOut
│   │   ├── service.py               # PerformanceBFFService
│   │   ├── dependencies.py
│   │   └── router.py                # GET /api/v1/bff/performance
│   │
│   ├── activities/
│   │   ├── schemas.py               # ActivitiesListOut, ActivityDetailOut
│   │   ├── service.py               # ActivitiesBFFService
│   │   ├── dependencies.py
│   │   └── router.py                # GET /api/v1/bff/activities...
│   │
│   ├── profile/
│   │   ├── schemas.py               # ProfileZonesOut
│   │   ├── service.py               # ProfileBFFService
│   │   ├── dependencies.py
│   │   └── router.py                # GET /api/v1/bff/profile/zones
│   │
│   └── shoes/
│       ├── schemas.py               # ShoesBFFOut
│       ├── service.py               # ShoesBFFService
│       ├── dependencies.py
│       └── router.py                # GET /api/v1/bff/shoes
│
├── main.py                          # Registers both domain + screen routers
└── core/
    ├── config.py
    └── di.py                        # Central DI container (optional, for complex wiring)
```

---

## Port Definitions (Protocols)

### Activity Repository
```python
# app/domain/activities/ports/repositories.py
from typing import Protocol, Sequence
from app.domain.activities.domain.entities import Activity, Split
from app.domain.activities.domain.value_objects import ActivityFilter

class ActivityRepository(Protocol):
    def get_by_id(self, id: int, user_id: int) -> Activity | None: ...
    def list(self, user_id: int, filter: ActivityFilter) -> Sequence[Activity]: ...
    def count(self, user_id: int, filter: ActivityFilter) -> int: ...
    def save(self, activity: Activity) -> Activity: ...
    def delete(self, id: int, user_id: int) -> bool: ...

class SplitRepository(Protocol):
    def get_by_activity(self, activity_id: int) -> Sequence[Split]: ...
    def save_batch(self, splits: Sequence[Split]) -> None: ...
```

### Zone Config Provider
```python
# app/domain/activities/ports/zone_config.py
from typing import Protocol
from app.domain.activities.domain.value_objects import ZoneConfig

class ZoneConfigProvider(Protocol):
    def get_for_user(self, user_id: int) -> ZoneConfig: ...
    def invalidate_cache(self, user_id: int) -> None: ...
```

### Health Repository
```python
# app/domain/health/ports/repositories.py
from typing import Protocol, Sequence
from datetime import date
from app.domain.health.domain.entities import SleepNight, HRVReading, RHRReading, StressReading

class HealthRepository(Protocol):
    def get_sleep_range(self, user_id: int, start: date, end: date) -> Sequence[SleepNight]: ...
    def get_hrv_range(self, user_id: int, start: date, end: date) -> Sequence[HRVReading]: ...
    def get_rhr_range(self, user_id: int, start: date, end: date) -> Sequence[RHRReading]: ...
    def get_stress_range(self, user_id: int, start: date, end: date) -> Sequence[StressReading]: ...
    def get_latest_hrv(self, user_id: int) -> HRVReading | None: ...
    def get_latest_sleep(self, user_id: int) -> SleepNight | None: ...
```

### AI Client (Evaluation)
```python
# app/domain/evaluation/ports/ai_client.py
from typing import Protocol
from app.domain.evaluation.domain.entities import EvaluationJob, Verdict

class AIClient(Protocol):
    async def evaluate(self, job: EvaluationJob, zone_config: ZoneConfig) -> Verdict: ...
    def estimate_tokens(self, prompt: str) -> int: ...
```

---

## Domain Entities (Examples)

### Activity
```python
# app/domain/activities/domain/entities.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from app.domain.activities.domain.value_objects import Pace, HeartRate, ZoneKey

@dataclass(frozen=True, slots=True)
class Split:
    idx: int
    distance_m: Optional[float]
    duration_s: Optional[float]
    pace: Optional[Pace]
    avg_hr: Optional[HeartRate]
    avg_cadence: Optional[int]
    elevation_m: Optional[float]
    intensity_type: Optional[str]
    zone: Optional[ZoneKey]
    km_label: str
    gct_ms: Optional[int] = None
    stride_cm: Optional[float] = None
    vert_osc_cm: Optional[float] = None
    vert_ratio: Optional[float] = None

@dataclass(frozen=True, slots=True)
class Activity:
    id: int
    user_id: int
    start_time: datetime
    activity_type: str
    name: Optional[str]
    distance_m: float
    duration_s: float
    avg_hr: Optional[HeartRate]
    max_hr: Optional[HeartRate]
    avg_cadence: Optional[int]
    elevation_gain_m: Optional[float]
    aerobic_te: Optional[float]
    anaerobic_te: Optional[float]
    training_load: Optional[float]
    inferred_type: Optional[str]
    structure: Optional[str]
    splits: tuple[Split, ...] = ()
    evaluated: bool = False
    
    @property
    def pace(self) -> Optional[Pace]:
        if self.duration_s and self.distance_m:
            return Pace.from_seconds_per_meter(self.duration_s / self.distance_m)
        return None
```

### VDOT Profile
```python
# app/domain/performance/domain/entities.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass(frozen=True, slots=True)
class VDOTProfile:
    current_vdot: float
    source: str  # "test", "race", "manual", "garmin"
    test_date: datetime
    test_distance_m: float
    test_time_s: float
    demonstrated_vdot: Optional[float] = None
    demonstrated_source: Optional[str] = None
    demonstrated_date: Optional[datetime] = None
```

---

## Domain Services (Pure Logic)

### Consistency Calculator
```python
# app/domain/activities/domain/services.py
from dataclasses import dataclass
from app.domain.activities.domain.entities import Activity, Split

@dataclass(frozen=True, slots=True)
class ConsistencyMetrics:
    first_half_pace_s: Optional[float]
    second_half_pace_s: Optional[float]
    balance_delta_s: Optional[float]
    balance_delta_pct: Optional[float]
    first_half_hr: Optional[int]
    second_half_hr: Optional[int]
    hr_drift_bpm: Optional[float]
    decoupling_pct: Optional[float]
    cadence_fade_spm: Optional[float]

class ConsistencyCalculator:
    """Pure domain logic — no I/O, fully deterministic."""
    
    def calculate(self, activity: Activity, splits: Sequence[Split]) -> Optional[ConsistencyMetrics]:
        if activity.distance_m < 8000 or len(splits) < 4:
            return None
        
        # ... pure calculation logic
        return ConsistencyMetrics(...)
```

### PMC Calculator
```python
# app/domain/training_load/domain/services.py
from dataclasses import dataclass
from datetime import date
from typing import Sequence
from app.domain.activities.domain.entities import Activity

@dataclass(frozen=True, slots=True)
class PMCDay:
    date: date
    ctl: Optional[float]
    atl: Optional[float]
    tsb: Optional[float]
    acwr: Optional[float]

@dataclass(frozen=True, slots=True)
class PMCCurve:
    days: int
    points: tuple[PMCDay, ...]
    current: PMCDay

class PMCCalculator:
    """Pure math — ATL/CTL/TSB/ACWR with configurable constants."""
    
    CTL_CONSTANT = 42
    ATL_CONSTANT = 7
    ACWR_WINDOW_DAYS = 28
    
    def compute(self, activities: Sequence[Activity]) -> PMCCurve:
        # ... pure calculation, no DB, no HTTP
        return PMCCurve(...)
```

---

## Application Services (Use Cases)

### Activity Service
```python
# app/domain/activities/service.py
from dataclasses import dataclass
from typing import Sequence
from app.domain.activities.ports.repositories import ActivityRepository, SplitRepository
from app.domain.activities.ports.zone_config import ZoneConfigProvider
from app.domain.activities.domain.services import ConsistencyCalculator
from app.domain.activities.domain.entities import Activity
from app.domain.activities.schemas import ActivityDetailOut, ActivityListOut, ActivityListItem

@dataclass
class ActivityService:
    repo: ActivityRepository
    split_repo: SplitRepository
    zone_provider: ZoneConfigProvider
    consistency: ConsistencyCalculator
    
    def get_detail(self, activity_id: int, user_id: int) -> ActivityDetailOut | None:
        activity = self.repo.get_by_id(activity_id, user_id)
        if not activity:
            return None
        
        splits = self.split_repo.get_by_activity(activity_id)
        zone_config = self.zone_provider.get_for_user(user_id)
        consistency = self.consistency.calculate(activity, splits)
        
        return ActivityDetailOut.from_domain(activity, splits, zone_config, consistency)
    
    def list(self, user_id: int, filter: ActivityFilter, limit: int, offset: int) -> ActivityListOut:
        activities = self.repo.list(user_id, filter, limit, offset)
        total = self.repo.count(user_id, filter)
        zone_config = self.zone_provider.get_for_user(user_id)
        
        items = [ActivityListItem.from_domain(a, zone_config) for a in activities]
        return ActivityListOut(items=items, total=total, limit=limit, offset=offset)
```

### Home BFF Service (Composition)
```python
# app/bff/home/service.py
from dataclasses import dataclass
from app.domain.activities.service import ActivityService
from app.domain.health.service import HealthService
from app.domain.training_load.service import TrainingLoadService
from app.domain.performance.service import PerformanceService
from app.domain.profile.service import ProfileService
from app.bff.home.schemas import HomeTodayOut

@dataclass
class HomeBFFService:
    activities: ActivityService
    health: HealthService
    training_load: TrainingLoadService
    performance: PerformanceService
    profile: ProfileService
    
    def get_today(self, user_id: int, tz: timezone) -> HomeTodayOut:
        # Compose from multiple domain services
        verdict = self.activities.get_today_verdict(user_id, tz)
        signals = self.health.get_signals(user_id, tz)
        strip = self.training_load.get_recent_strip(user_id, days=28)
        last_activity = self.activities.get_last_running(user_id)
        volume = self.training_load.get_week_volume(user_id, tz)
        countdown = self.performance.get_next_race(user_id, tz)
        recommendations = self.activities.get_recommendations(user_id, signals, volume)
        
        # P2 data
        volume_weeks = self.training_load.get_volume_weeks(user_id, weeks=10)
        predictions = self.performance.get_predictions_digest(user_id)
        
        return HomeTodayOut(
            date=tz.today(),
            verdict=verdict,
            signals=signals,
            strip=strip,
            last_activity=last_activity,
            volume=volume,
            countdown=countdown,
            recommendations=recommendations,
            volume_weeks=volume_weeks,
            predictions=predictions,
        )
```

---

## DI Wiring (FastAPI Depends)

### Per-Domain Dependencies
```python
# app/domain/activities/dependencies.py
from fastapi import Depends
from sqlalchemy.orm import Session
from app.db.engine import get_db
from app.domain.activities.ports.repositories import ActivityRepository, SplitRepository
from app.domain.activities.ports.zone_config import ZoneConfigProvider
from app.domain.activities.adapters.sqlalchemy_repo import SQLAlchemyActivityRepository, SQLAlchemySplitRepository
from app.domain.activities.adapters.db_zone_config import DBZoneConfigProvider
from app.domain.activities.domain.services import ConsistencyCalculator
from app.domain.activities.service import ActivityService

def get_activity_repo(db: Session = Depends(get_db)) -> ActivityRepository:
    return SQLAlchemyActivityRepository(db)

def get_split_repo(db: Session = Depends(get_db)) -> SplitRepository:
    return SQLAlchemySplitRepository(db)

def get_zone_provider(db: Session = Depends(get_db)) -> ZoneConfigProvider:
    return DBZoneConfigProvider(db)

def get_consistency() -> ConsistencyCalculator:
    return ConsistencyCalculator()

def get_activity_service(
    repo: ActivityRepository = Depends(get_activity_repo),
    split_repo: SplitRepository = Depends(get_split_repo),
    zone_provider: ZoneConfigProvider = Depends(get_zone_provider),
    consistency: ConsistencyCalculator = Depends(get_consistency),
) -> ActivityService:
    return ActivityService(repo, split_repo, zone_provider, consistency)
```

### BFF Dependencies
```python
# app/bff/home/dependencies.py
from fastapi import Depends
from app.domain.activities.dependencies import get_activity_service
from app.domain.health.dependencies import get_health_service
from app.domain.training_load.dependencies import get_training_load_service
from app.domain.performance.dependencies import get_performance_service
from app.domain.profile.dependencies import get_profile_service
from app.bff.home.service import HomeBFFService

def get_home_bff_service(
    activities: ActivityService = Depends(get_activity_service),
    health: HealthService = Depends(get_health_service),
    training_load: TrainingLoadService = Depends(get_training_load_service),
    performance: PerformanceService = Depends(get_performance_service),
    profile: ProfileService = Depends(get_profile_service),
) -> HomeBFFService:
    return HomeBFFService(activities, health, training_load, performance, profile)
```

---

## Router Examples

### Domain Router (Activities)
```python
# app/domain/activities/router.py
from fastapi import APIRouter, Depends, Query
from app.auth.deps import require_session
from app.db.models import User
from app.domain.activities.dependencies import get_activity_service
from app.domain.activities.service import ActivityService
from app.domain.activities.schemas import ActivityListOut, ActivityDetailOut

router = APIRouter(prefix="/api/v1/activities", tags=["activities"])

@router.get("")
def list_activities(
    activity_type: str = Query("running", pattern="^(running|all)$"),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_session),
    service: ActivityService = Depends(get_activity_service),
) -> ActivityListOut:
    from app.domain.activities.domain.value_objects import ActivityFilter
    filter = ActivityFilter(type=activity_type)
    return service.list(user.id, filter, limit, offset)

@router.get("/{activity_id}")
def get_activity(
    activity_id: int,
    user: User = Depends(require_session),
    service: ActivityService = Depends(get_activity_service),
) -> ActivityDetailOut:
    detail = service.get_detail(activity_id, user.id)
    if not detail:
        raise HTTPException(404, "atividade não encontrada")
    return detail
```

### BFF Router (Home)
```python
# app/bff/home/router.py
from fastapi import APIRouter, Depends
from app.auth.deps import require_session
from app.db.models import User
from app.core.tz import app_tz
from app.bff.home.dependencies import get_home_bff_service
from app.bff.home.service import HomeBFFService
from app.bff.home.schemas import HomeTodayOut

router = APIRouter(prefix="/api/v1/bff/home", tags=["bff:home"])

@router.get("/today")
def get_home_today(
    user: User = Depends(require_session),
    service: HomeBFFService = Depends(get_home_bff_service),
) -> HomeTodayOut:
    return service.get_today(user.id, app_tz())
```

---

## Migration Strategy (Strangler Fig)

### Phase 1: Extract Domain Layer (Week 1-3)
1. Create `app/domain/` structure
2. Move pure logic from `service.py` → `domain/services.py`
3. Define Protocols for repositories
4. Create SQLAlchemy adapters
5. Wire DI, add domain routers at `/api/v1/...`
6. **Old routers unchanged**

### Phase 2: BFF Composition Layer (Week 4-5)
1. Create `app/bff/` with BFF services
2. BFF services compose domain services
3. Add BFF routers at `/api/v1/bff/...`
4. **Old endpoints delegate to BFF services:**
```python
# OLD: app/home/router.py (becomes thin delegate)
@router.get("/today")
def get_home_today(
    user: User = Depends(require_session),
    db: Session = Depends(get_db),
) -> HomeOut:
    # Delegate to new BFF service
    from app.bff.home.dependencies import get_home_bff_service
    from app.bff.home.service import HomeBFFService
    # ... construct service with existing DB session
    return service.get_today(user.id, app_tz())
```

### Phase 3: Frontend Migration (Week 6-8)
1. Set up OpenAPI → TypeScript codegen
2. Migrate screens one by one:
   - Home → `/api/v1/bff/home/today`
   - Health → `/api/v1/bff/health/summary`
   - Performance → `/api/v1/bff/performance`
   - Treinos → `/api/v1/bff/activities`
   - Perfil → `/api/v1/bff/profile/zones`
   - Equipamentos → `/api/v1/bff/shoes`
3. Each screen migration = 1 PR, deploy independently

### Phase 4: Deprecate Old Endpoints (Week 9)
1. After all screens migrated, old endpoints return 410
2. Remove old router code
3. Clean up unused imports

---

## OpenAPI / TypeScript Codegen

### Backend: OpenAPI Tags
```python
# app/main.py
app = FastAPI(
    title="Ritmo API",
    version="1.0.0",
    openapi_tags=[
        {"name": "activities", "description": "Domain: Activities & Splits"},
        {"name": "training-load", "description": "Domain: PMC, Volume, ATL/CTL"},
        {"name": "health", "description": "Domain: Sleep, HRV, RHR, Stress"},
        {"name": "performance", "description": "Domain: VDOT, Predictions, Decay"},
        {"name": "shoes", "description": "Domain: Shoes, Analysis, Degradation"},
        {"name": "evaluation", "description": "Domain: AI Evaluation Jobs"},
        {"name": "profile", "description": "Domain: HR Zones, Pace Zones, Settings"},
        {"name": "garmin", "description": "Integration: Garmin Sync"},
        # BFF tags
        {"name": "bff:home", "description": "BFF: Home Dashboard"},
        {"name": "bff:health", "description": "BFF: Health Panel"},
        {"name": "bff:performance", "description": "BFF: Performance Panel"},
        {"name": "bff:activities", "description": "BFF: Treinos List/Detail"},
        {"name": "bff:profile", "description": "BFF: Profile Zones"},
        {"name": "bff:shoes", "description": "BFF: Equipamentos"},
    ],
)
```

### Frontend: Codegen Setup
```json
// frontend/package.json
{
  "scripts": {
    "generate:api": "openapi-typescript http://localhost:8000/openapi.json -o src/lib/generated/api.ts",
    "dev": "npm run generate:api && next dev"
  }
}
```

```typescript
// frontend/src/lib/domain-api.ts (generated, not edited)
export interface Activity { ... }
export interface ActivityDetailOut { ... }
export interface PMCCurve { ... }
export interface VDOTProfile { ... }

// frontend/src/lib/bff-api.ts (generated)
export interface HomeTodayOut { ... }
export interface HealthSummaryOut { ... }
```

---

## Testing Strategy

| Layer | Test Type | Approach |
|-------|-----------|----------|
| Domain Core | Unit | Pure functions, property-based testing (hypothesis) |
| Domain Services | Unit | Real domain objects, mock ports (Protocol) |
| Adapters | Integration | Testcontainers (PostgreSQL), real Garmin API (recorded) |
| Application Services | Unit | Mock ports, verify orchestration |
| Domain Routers | Integration | TestClient, verify serialization |
| Screen Services | Unit | Mock domain services, verify composition |
| Screen Routers | Integration | TestClient, verify payload shape matches spec |
| Contract | Snapshot | OpenAPI schema snapshot in CI |

---

## Decision Log (ADRs)

| ADR | Decision |
|-----|----------|
| ADR-001 | Use `Protocol` for ports (structural typing, mypy, no runtime cost) |
| ADR-002 | Use FastAPI `Depends` for DI (native, no container needed) |
| ADR-003 | Domain entities as frozen `@dataclass(slots=True)` (immutable, fast) |
| ADR-004 | Pydantic only at API boundary (schemas.py), not in domain core |
| ADR-005 | BFF composition in same process (modular monolith, no network hop) |
| ADR-006 | Old endpoints delegate to BFF layer during migration |
| ADR-007 | OpenAPI → TypeScript codegen at build time (CI) |
| ADR-008 | Domain API versioned independently (`/api/v1/`) from BFF API (`/api/v1/bff/`) |

---

## Complexity Assessment

| Phase | Tasks | Est. Weeks | Risk |
|-------|-------|------------|------|
| 1. Domain Layer | 12 | 3 | Low (mechanical extraction) |
| 2. Screen Layer | 6 | 2 | Low (thin composition) |
| 3. Frontend Migration | 8 | 3 | Medium (coordination) |
| 4. Codegen + Deprecation | 4 | 1 | Low |
| **Total** | **30** | **~9** | **Medium** |

**Parallelizable:** Domain contexts (activities, health, performance, shoes, profile) can be extracted independently.