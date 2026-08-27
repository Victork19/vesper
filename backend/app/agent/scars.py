from datetime import datetime,timezone,timedelta
import uuid
from ..memory.models import *
class ScarEngine:
    def __init__(self,memory):self.memory=memory
    def create(self,lesson,context,severity=8,kind='decision_failure',impact=None,decision_class='general'):
        impact=impact or Impact(trust_delta=-min(.5,severity/20),size_multiplier=max(.2,1-severity/10),force_do_nothing=severity>=9)
        cooldown=(datetime.now(timezone.utc)+timedelta(hours=max(1,severity*2))).replace(microsecond=0).isoformat().replace('+00:00','Z') if severity>=7 else None
        s=Scar(id='scar_'+datetime.now(timezone.utc).strftime('%Y%m%d')+'_'+uuid.uuid4().hex[:5],type=kind,severity=severity,lesson=lesson,principle='Use independent verification and a reversible test before repeating this class of decision.',context=context,decision_class=decision_class,cooldown_until=cooldown,impact=impact)
        self.memory.save_scar(s); self.memory.journal('scar_created',s.model_dump()); return s
    def reinforce(self,scar_id):
        s=self.memory.get_scar(scar_id)
        if s:s.severity=min(10,s.severity+1); self.memory.save_scar(s)
