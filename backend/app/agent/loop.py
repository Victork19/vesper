from .decision import decide
from .constitution import Guardian
from .scars import ScarEngine
from .principles import PrincipleEngine
class AgentLoop:
    def __init__(self,memory,llm=None): self.memory=memory; self.llm=llm; self.guardian=Guardian(memory); self.scars_engine=ScarEngine(memory); self.principles_engine=PrincipleEngine(memory)
    def decision(self,req):
        hot=self.memory.get_hot(); d=decide(req.situation,req.choices,self.memory.scars(True),self.memory.principles(),hot,self.guardian,self.llm,req.execute); hot.last_decision_context=req.situation; hot.active_constraints=d.cited_principles; self.memory.set_hot(hot); self.memory.save_decision(d); self.memory.journal('decision',d.model_dump()); return d
    def failure(self,lesson,context,severity=8):
        s=self.scars_engine.create(lesson,context,severity); p=self.principles_engine.consolidate(s); hot=self.memory.get_hot(); hot.trust_score=max(0,hot.trust_score+s.impact.trust_delta); hot.active_cooldowns[s.id]=s.cooldown_until or ''; hot.active_constraints=list(dict.fromkeys(hot.active_constraints+[p.id])); self.memory.set_hot(hot); return s
