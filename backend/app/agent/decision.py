import uuid
from .temporal import active_scars,in_cooldown
from ..memory.models import DecisionRecord
def decide(situation,choices,scars,principles,hot,guardian,llm=None,execute=False):
    remembered=scars; sleeping=in_cooldown(scars); words=set(situation.lower().split())
    relevant=[s for s in remembered if any(w in (s.lesson+' '+s.context+' '+s.principle).lower() for w in words if len(w)>4)]
    relevant=relevant or remembered[:3]; relevant_principles=[p for p in principles if any(x in p.source_scars for x in [s.id for s in relevant])]
    risk=min(10,max(3,(max((s.severity for s in relevant),default=0)+1)))
    trust=max(0,min(1,hot.trust_score-sum(max(0,-s.impact.trust_delta) for s in relevant)))
    forced=any(s.impact.force_do_nothing for s in relevant) or (len(sleeping)>=2)
    action='DO NOTHING' if forced else ('REFUSE / REQUEST MORE EVIDENCE' if relevant else (choices[0] if choices else 'PROCEED WITH SMALL REVERSIBLE TEST'))
    blocked,msg=guardian.guard(action,risk,forced)
    if blocked:action='DO NOTHING'
    rationale=(msg+' ' if msg else '')+('Recalled scars: '+ '; '.join(f'{s.id} — {s.lesson}' for s in relevant) if relevant else 'No matching scars were recalled; this is the naive baseline.')
    if relevant_principles:rationale+=' Rules tightened: '+ '; '.join(p.statement for p in relevant_principles)
    return DecisionRecord(id='decision_'+uuid.uuid4().hex[:10],situation=situation,choices=choices,action=action,confidence=max(.1,min(.95,trust-(risk*.03))),risk_score=risk,rationale=rationale,cited_scars=[s.id for s in relevant],cited_principles=[p.id for p in relevant_principles],outcome='executed' if execute and action!='DO NOTHING' else 'proposed',memory_enabled=True)
