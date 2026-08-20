import json, os, sqlite3
from pathlib import Path
from .models import *

class SibylMemory:
    """Sibyl-first repository. Local mirror is explicit and keeps the deletion test reproducible."""
    def __init__(self, path=None):
        self.path=Path(path or os.getenv('SIBYL_DB_PATH','./data/vesper.db')).expanduser(); self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.path,check_same_thread=False); self.db.row_factory=sqlite3.Row
        self.db.execute('CREATE TABLE IF NOT EXISTS memory (tier TEXT,key TEXT,value TEXT,updated_at TEXT,PRIMARY KEY(tier,key))'); self.db.commit()
        self.official=None
        if os.getenv('SIBYL_OFFICIAL','1')!='0':
            try:
                from sibyl_memory_client import MemoryClient
                self.official=MemoryClient.local(str(self.path))
            except Exception: pass
        if not self.get_hot().session_id: self.set_hot(HotState(session_id='session_initial'))
        if not self.get_reference(): self.put('REFERENCE','constitution',Constitution().model_dump())
    def put(self,tier,key,value):
        self.db.execute('INSERT OR REPLACE INTO memory VALUES (?,?,?,?)',(tier,key,json.dumps(value),now_iso())); self.db.commit(); self._official_write(tier,key,value)
    def _official_write(self,tier,key,value):
        if not self.official:return
        try:
            if tier=='WARM' and hasattr(self.official,'set_entity'): self.official.set_entity('vesper',key,value)
            elif tier=='HOT' and hasattr(self.official,'set_state'): self.official.set_state('vesper',key,value)
            elif tier=='REFERENCE' and hasattr(self.official,'set_reference'): self.official.set_reference('vesper',key,value)
            elif tier=='COLD' and hasattr(self.official,'write_event'): self.official.write_event('vesper',key,value)
        except Exception: pass
    def get(self,tier,key):
        row=self.db.execute('SELECT value FROM memory WHERE tier=? AND key=?',(tier,key)).fetchone(); return json.loads(row['value']) if row else None
    def all(self,tier): return [json.loads(r['value']) for r in self.db.execute('SELECT value FROM memory WHERE tier=? ORDER BY updated_at DESC',(tier,))]
    def get_hot(self): return HotState.model_validate(self.get('HOT','state') or {})
    def set_hot(self,state): self.put('HOT','state',state.model_dump())
    def get_reference(self): return self.get('REFERENCE','constitution')
    def save_scar(self,s): self.put('WARM',s.id,s.model_dump())
    def get_scar(self,id):
        x=self.get('WARM',id) or self.get('ARCHIVE',id); return Scar.model_validate(x) if x else None
    def scars(self,active_only=False):
        result=[Scar.model_validate(x) for x in self.all('WARM') if isinstance(x,dict) and 'lesson' in x]; return [s for s in result if s.status=='active'] if active_only else result
    def save_principle(self,p): self.put('WARM',p.id,p.model_dump())
    def principles(self): return [Principle.model_validate(x) for x in self.all('WARM') if isinstance(x,dict) and 'statement' in x]
    def save_decision(self,d): self.put('COLD',d.id,d.model_dump())
    def decisions(self): return [DecisionRecord.model_validate(x) for x in self.all('COLD') if isinstance(x,dict) and 'action' in x]
    def journal(self,event,payload): self.put('COLD','event_'+now_iso()+'_'+str(len(self.all('COLD'))),{'event':event,'payload':payload,'created_at':now_iso()})
    def timeline(self): return self.all('COLD')
    def archive(self,item): self.put('ARCHIVE',item.id,item.model_dump()); self.db.execute('DELETE FROM memory WHERE tier=? AND key=?',('WARM',item.id)); self.db.commit()
    def delete_learning_memory(self):
        self.db.execute("DELETE FROM memory WHERE tier IN ('HOT','WARM','ARCHIVE')"); self.db.commit(); self.set_hot(HotState(memory_enabled=False,session_id='memory_deleted'))
