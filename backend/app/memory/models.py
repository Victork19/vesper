from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field

Tier = Literal['HOT','WARM','COLD','REFERENCE','ARCHIVE']
def now_iso(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')

class Impact(BaseModel):
    trust_delta: float = -0.1
    size_multiplier: float = 0.8
    new_filters: list[str] = Field(default_factory=list)
    force_do_nothing: bool = False

class Scar(BaseModel):
    id: str
    type: str = 'decision_failure'
    severity: int = Field(ge=1, le=10)
    lesson: str
    principle: str
    context: str = ''
    created_at: str = Field(default_factory=now_iso)
    cooldown_until: str | None = None
    impact: Impact = Field(default_factory=Impact)
    status: str = 'active'
    linked_principles: list[str] = Field(default_factory=list)
    onchain_tx: str | None = None
    onchain_hash: str | None = None
    anchor_status: str | None = None
    anchor_request_id: str | None = None
    anchor_approval_url: str | None = None

class Principle(BaseModel):
    id: str
    statement: str
    source_scars: list[str] = Field(default_factory=list)
    strength: int = Field(default=1, ge=1, le=10)
    created_at: str = Field(default_factory=now_iso)
    status: str = 'active'

class HotState(BaseModel):
    memory_enabled: bool = True
    trust_score: float = Field(default=0.5, ge=0, le=1)
    active_constraints: list[str] = Field(default_factory=list)
    active_cooldowns: dict[str,str] = Field(default_factory=dict)
    open_loops: list[str] = Field(default_factory=list)
    last_decision_context: str = ''
    session_id: str = ''

class Constitution(BaseModel):
    name: str = 'Vesper hard limits'
    rules: list[str] = Field(default_factory=lambda: [
        'Never claim certainty when evidence is incomplete.',
        'Never increase risk after a failure.',
        'Prefer doing nothing over an irreversible high-risk action.',
        'Never remove a validated rule because of a new scar.'
    ])

class DecisionRequest(BaseModel):
    situation: str = Field(min_length=8,max_length=2000)
    choices: list[str] = Field(default_factory=list)
    execute: bool = False

class OutcomeRequest(BaseModel):
    decision_id: str
    outcome: Literal['success','failure','loss','negative','cancelled'] = 'failure'
    lesson: str = Field(default='The decision produced a negative outcome.',min_length=8,max_length=2000)
    context: str = Field(default='',max_length=4000)
    severity: int = Field(default=7,ge=1,le=10)

class ScenarioRequest(BaseModel):
    scenario: Literal['irreversible_transfer','production_deploy','treasury_payment'] = 'irreversible_transfer'

class DecisionRecord(BaseModel):
    id: str
    created_at: str = Field(default_factory=now_iso)
    situation: str
    choices: list[str] = Field(default_factory=list)
    action: str
    confidence: float = Field(ge=0, le=1)
    risk_score: int = Field(ge=0, le=10)
    rationale: str
    cited_scars: list[str] = Field(default_factory=list)
    cited_principles: list[str] = Field(default_factory=list)
    outcome: str = 'pending'
    generated_scar_id: str | None = None
    memory_enabled: bool = True

class AnchorResult(BaseModel):
    scar_id: str
    canonical_hash: str
    transaction_hash: str | None = None
    explorer_url: str | None = None
    approval_url: str | None = None
    request_id: str | None = None
    status: str
