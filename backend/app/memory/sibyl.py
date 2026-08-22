"""Authoritative Sibyl Memory repository for Vesper."""
import json, os
from .models import *
from sibyl_memory_client.exceptions import NotFoundError

class SibylMemory:
    def __init__(self):
        from sibyl_memory_client import MemoryClient
        self.path=os.getenv('SIBYL_MEMORY_PATH','/app/data/sibyl-memory.db')
        self.tenant=os.getenv('SIBYL_TENANT_ID','vesper')
        self.official=MemoryClient.local(self.path,tenant_id=self.tenant)
        self.official_error=None
        if not self._get_state('state'):
            self._set_state('state',HotState(session_id='session_initial').model_dump())
        if not self._get_reference('constitution'):
            self._set_reference('constitution',Constitution().model_dump())

    @staticmethod
    def _body(row): return row.get('body') if isinstance(row,dict) and 'body' in row else row
    def _set_entity(self,key,value,category='vesper'): return self.official.set_entity(category,key,value)
    def _get_entity(self,key,category='vesper'):
        try:return self._body(self.official.get_entity(category,key))
        except NotFoundError:return None
    def _set_state(self,key,value): self.official.set_state(key,value)
    def _get_state(self,key):
        row=self.official.get_state(key); return self._body(row) if row else None
    def _set_reference(self,key,value): self.official.set_reference(key,value)
    def _get_reference(self,key):
        row=self.official.get_reference(key)
        if not row:return None
        body=self._body(row)
        if isinstance(body,str):
            try:return json.loads(body)
            except json.JSONDecodeError:return body
        return body
    def _entities(self,category='vesper'):
        return [self._body(x) for x in self.official.list_entities(category=category,limit=10000)]
    def put(self,tier,key,value):
        if tier=='WARM': self._set_entity(key,value)
        elif tier=='HOT': self._set_state(key,value)
        elif tier=='REFERENCE': self._set_reference(key,value)
        elif tier=='ARCHIVE': self._set_entity(key,value,'vesper_archive')
        elif tier=='COLD': self.official.write_event(extra={'key':key,'value':value})
    def get(self,tier,key):
        if tier=='WARM':return self._get_entity(key)
        if tier=='HOT':return self._get_state(key)
        if tier=='REFERENCE':return self._get_reference(key)
        if tier=='ARCHIVE':return self._get_entity(key,'vesper_archive')
        if tier=='COLD':
            for event in self.official.read_events(limit=10000):
                extra=event.get('extra') or {}
                if extra.get('key')==key:return extra.get('value')
        return None
    def all(self,tier):
        if tier=='WARM':return self._entities()
        if tier=='ARCHIVE':return self._entities('vesper_archive')
        if tier=='COLD':return [x.get('extra',{}).get('value') for x in self.official.read_events(limit=10000) if (x.get('extra') or {}).get('value') is not None]
        return []
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
    def decisions(self):
        latest={}
        for item in self.all('COLD'):
            if isinstance(item,dict) and 'action' in item: latest[item['id']]=item
        return [DecisionRecord.model_validate(item) for item in latest.values()]
    def journal(self,event,payload): self.put('COLD','event_'+now_iso()+'_'+str(len(self.all('COLD'))),{'event':event,'payload':payload,'created_at':now_iso()})
    def timeline(self): return self.all('COLD')
    def archive(self,item): self.put('ARCHIVE',item.id,item.model_dump())
    def delete_learning_memory(self):
        for item in self._entities():
            if isinstance(item,dict) and ('lesson' in item or 'statement' in item): self.official.delete_entity('vesper',item.get('id',''))
        for item in self._entities('vesper_archive'):
            if isinstance(item,dict): self.official.delete_entity('vesper_archive',item.get('id',''))
        self._set_state('state',HotState(memory_enabled=False,session_id='memory_deleted').model_dump())
