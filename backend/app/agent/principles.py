from ..memory.models import Principle
import uuid
class PrincipleEngine:
    def __init__(self,memory):self.memory=memory
    def consolidate(self,scar):
        existing=next((p for p in self.memory.principles() if p.statement.lower()==scar.principle.lower()),None)
        if existing: existing.source_scars=list(dict.fromkeys(existing.source_scars+[scar.id])); existing.strength=min(10,existing.strength+1); self.memory.save_principle(existing); return existing
        p=Principle(id='principle_'+uuid.uuid4().hex[:7],statement=scar.principle,source_scars=[scar.id],strength=max(1,scar.severity//2)); self.memory.save_principle(p); scar.linked_principles=[p.id]; self.memory.save_scar(scar); self.memory.journal('principle_created',p.model_dump()); return p
