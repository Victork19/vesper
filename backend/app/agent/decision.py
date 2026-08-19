from .prompts import SYSTEM_PROMPT
from ..memory.models import DecisionRecord, now_iso
import uuid

def decide(situation: str, scars, memory_enabled=True, execute=False, llm=None):
    relevant = [s for s in scars if any(word in (s.context+' '+s.lesson+' '+s.impact).lower() for word in situation.lower().split() if len(word)>4)] if memory_enabled else []
    relevant = relevant[:3]
    highest = max((s.severity for s in relevant), default=0)
    risk = min(10, max(3, highest + 1 if relevant else 5))
    action = 'REFUSE / REQUEST MORE EVIDENCE' if relevant else 'PROCEED WITH SMALL REVERSIBLE TEST'
    rationale = ('Memory constraint triggered: ' + '; '.join(f'{s.id}: {s.lesson}' for s in relevant)) if relevant else 'No matching operational scar was available; apply a bounded, reversible test.'
    if llm:
        generated=llm.complete(situation,[s.model_dump() for s in relevant])
        if generated:
            action=str(generated.get('action',action)); rationale=str(generated.get('rationale',rationale)); risk=int(generated.get('risk_score',risk)); cited=list(dict.fromkeys(generated.get('cited_scars',[])+[s.id for s in relevant]))
            return DecisionRecord(id='decision_'+uuid.uuid4().hex[:10], situation=situation, action=action, rationale=rationale, risk_score=max(0,min(10,risk)), outcome='executed' if execute else 'proposed', cited_scars=cited, memory_enabled=memory_enabled)
    return DecisionRecord(id='decision_'+uuid.uuid4().hex[:10], situation=situation, action=action, rationale=rationale, risk_score=risk, outcome='executed' if execute else 'proposed', cited_scars=[s.id for s in relevant], memory_enabled=memory_enabled)
