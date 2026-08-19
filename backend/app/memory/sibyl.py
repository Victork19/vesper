import json, os, sqlite3
from pathlib import Path
from .models import Scar, DecisionRecord, HotState, now_iso

class SibylMemory:
    """Local-first Sibyl-compatible memory with explicit official tiers."""
    def __init__(self, path: str | None = None):
        self.path = Path(path or os.getenv('SIBYL_DB_PATH', './data/vesper.db')).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''CREATE TABLE IF NOT EXISTS memory (tier TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(tier,key));''')
        self.db.commit()
        self.official = None
        if os.getenv('SIBYL_OFFICIAL','1') != '0':
            try:
                from sibyl_memory_client import MemoryClient
                self.official = MemoryClient.local(str(self.path))
            except Exception:
                self.official = None
        if not self.get_hot().session_bridge:
            self.set_hot(HotState(session_bridge='Session initialized. Memory is load-bearing.'))

    def put(self, tier: str, key: str, value: object):
        self.db.execute('INSERT OR REPLACE INTO memory VALUES (?,?,?,?)', (tier, key, json.dumps(value), now_iso()))
        self.db.commit()
        if self.official:
            try:
                if tier == 'WARM' and hasattr(self.official,'set_entity'):
                    self.official.set_entity('vesper', key, value)
                elif tier == 'HOT' and hasattr(self.official,'set_state'):
                    self.official.set_state('vesper', key, value)
                elif tier == 'REFERENCE' and hasattr(self.official,'set_reference'):
                    self.official.set_reference('vesper', key, value)
                elif tier == 'COLD' and hasattr(self.official,'write_event'):
                    self.official.write_event('vesper', key, value)
            except Exception:
                pass
    def get(self, tier: str, key: str):
        row = self.db.execute('SELECT value FROM memory WHERE tier=? AND key=?', (tier,key)).fetchone()
        return json.loads(row['value']) if row else None
    def all(self, tier: str):
        return [json.loads(r['value']) for r in self.db.execute('SELECT value FROM memory WHERE tier=? ORDER BY updated_at DESC',(tier,))]
    def set_hot(self, state: HotState): self.put('HOT','state',state.model_dump())
    def get_hot(self): return HotState.model_validate(self.get('HOT','state') or {})
    def save_scar(self, scar: Scar): self.put('WARM', scar.id, scar.model_dump())
    def get_scar(self, scar_id: str):
        item = self.get('WARM', scar_id) or self.get('ARCHIVE', scar_id)
        return Scar.model_validate(item) if item else None
    def scars(self, active_only=False):
        items = [Scar.model_validate(x) for x in self.all('WARM')]
        return [s for s in items if s.status == 'active'] if active_only else items
    def save_decision(self, d: DecisionRecord): self.put('COLD', d.id, d.model_dump())
    def decisions(self): return [DecisionRecord.model_validate(x) for x in self.all('COLD')]
    def journal(self, event: str, payload: object): self.put('COLD', f'event_{now_iso()}_{len(self.all("COLD"))}', {'event':event,'payload':payload,'created_at':now_iso()})
    def archive(self, scar: Scar): self.put('ARCHIVE', scar.id, scar.model_dump()); self.db.execute('DELETE FROM memory WHERE tier="WARM" AND key=?',(scar.id,)); self.db.commit()
