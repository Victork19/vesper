from .decision import decide
from ..memory.models import Scar, HotState, now_iso
import uuid

class AgentLoop:
    def __init__(self, memory, anchor, llm=None): self.memory, self.anchor, self.llm = memory, anchor, llm
    def decision(self, situation, execute=False):
        d = decide(situation, self.memory.scars(True), self.memory.get_hot().session_bridge != 'MEMORY_DISABLED', execute, self.llm)
        self.memory.save_decision(d); self.memory.journal('decision', d.model_dump())
        return d
    def create_scar(self, data: dict):
        scar = Scar(id=data.get('id') or f'scar_{now_iso()[:10].replace("-","")}_{uuid.uuid4().hex[:3]}', **{k:v for k,v in data.items() if k != 'id'})
        self.memory.save_scar(scar); self.memory.journal('scar_created', scar.model_dump())
        return scar
