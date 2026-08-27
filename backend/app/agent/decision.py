import uuid
from .temporal import in_cooldown
from ..memory.models import DecisionRecord

SAFE_ACTIONS={'DO NOTHING','REFUSE / REQUEST MORE EVIDENCE','PROCEED WITH SMALL REVERSIBLE TEST'}

def classify_situation(situation):
    text=situation.lower()
    if any(word in text for word in ('deploy','production','rollback','release')): return 'production_deploy'
    if any(word in text for word in ('treasury','payment','payee')): return 'treasury_payment'
    if any(word in text for word in ('transfer','wallet','destination','address')): return 'irreversible_transfer'
    return 'general'

def decide(situation,choices,scars,principles,hot,guardian,llm=None,execute=False,decision_class=None,situation_id=None):
    decision_class=decision_class or classify_situation(situation)
    situation_id=situation_id or decision_class
    sleeping=in_cooldown(scars); words=set(situation.lower().split())
    class_matches=[s for s in scars if s.decision_class == decision_class and decision_class != 'general']
    word_matches=[s for s in scars if any(w in (s.lesson+' '+s.context+' '+s.principle).lower() for w in words if len(w)>4)]
    relevant=[]
    for scar in class_matches+word_matches:
        if scar.id not in {item.id for item in relevant}: relevant.append(scar)
    relevant=(relevant[:3] or scars[:3])
    relevant_principles=[p for p in principles if any(x in p.source_scars for x in [s.id for s in relevant])]
    risk=min(10,max(3,(max((s.severity for s in relevant),default=0)+1)))
    trust=max(0,min(1,hot.trust_score-sum(max(0,-s.impact.trust_delta) for s in relevant)))
    forced=any(s.impact.force_do_nothing for s in relevant) or len(sleeping)>=2
    action='DO NOTHING' if forced else ('REFUSE / REQUEST MORE EVIDENCE' if relevant else (choices[0] if choices else 'PROCEED WITH SMALL REVERSIBLE TEST'))
    llm_result=None
    if llm and getattr(llm,'enabled',False):
        try: llm_result=llm.complete(situation,[s.model_dump() for s in relevant])
        except Exception: llm_result=None
    if isinstance(llm_result,dict):
        proposed=llm_result.get('action'); allowed=set(choices)|SAFE_ACTIONS
        if isinstance(proposed,str) and proposed in allowed and not forced: action=proposed
        if isinstance(llm_result.get('risk_score'),(int,float)) and not forced:risk=max(0,min(10,int(llm_result['risk_score'])))
        cited=[x for x in llm_result.get('cited_scars',[]) if x in {s.id for s in relevant}]
        if cited: relevant=[s for s in relevant if s.id in cited]
    blocked,msg=guardian.guard(action,risk,forced)
    if blocked:action='DO NOTHING'
    llm_rationale=llm_result.get('rationale')+' ' if isinstance(llm_result,dict) and isinstance(llm_result.get('rationale'),str) else ''
    rationale=(msg+' ' if msg else '')+llm_rationale+('Recalled scars: '+ '; '.join(f'{s.id} — {s.lesson}' for s in relevant) if relevant else 'No matching scars were recalled; this is the naive baseline.')
    if relevant_principles:rationale+=' Rules tightened: '+ '; '.join(p.statement for p in relevant_principles)
    if execute:
        rationale+=' Execution was not performed: Vesper only proposes or blocks actions until an approved executor is connected.'
    return DecisionRecord(id='decision_'+uuid.uuid4().hex[:10],situation=situation,situation_id=situation_id,decision_class=decision_class,choices=choices,action=action,confidence=max(.1,min(.95,trust-(risk*.03))),risk_score=risk,rationale=rationale,cited_scars=[s.id for s in relevant],cited_principles=[p.id for p in relevant_principles],outcome='proposed',memory_enabled=True)
