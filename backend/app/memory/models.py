from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field

Tier = Literal['HOT', 'WARM', 'COLD', 'REFERENCE', 'ARCHIVE']

def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')

class Scar(BaseModel):
    id: str
    type: str = 'decision_failure'
    severity: int = Field(ge=1, le=10)
    created_at: str = Field(default_factory=now_iso)
    context: str
    lesson: str
    impact: str
    status: str = 'active'
    related_scars: list[str] = []
    onchain_tx: str | None = None
    onchain_hash: str | None = None
    raw_event_ref: str | None = None

class DecisionRequest(BaseModel):
    situation: str
    execute: bool = False

class DecisionRecord(BaseModel):
    id: str
    created_at: str = Field(default_factory=now_iso)
    situation: str
    action: str
    rationale: str
    risk_score: int = Field(ge=0, le=10)
    outcome: str = 'pending'
    cited_scars: list[str] = []
    memory_enabled: bool = True

class HotState(BaseModel):
    current_risk_posture: str = 'guarded'
    active_constraints: list[str] = []
    open_loops: list[str] = []
    session_bridge: str = ''

class Identity(BaseModel):
    name: str = 'Vesper'
    network: str = 'Base'
    address: str | None = None
    connected: bool = False
    anchored_scars: int = 0

class AnchorResult(BaseModel):
    scar_id: str
    canonical_hash: str
    transaction_hash: str | None = None
    explorer_url: str | None = None
    approval_url: str | None = None
    request_id: str | None = None
    status: str
