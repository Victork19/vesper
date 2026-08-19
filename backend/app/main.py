import os,uuid
from fastapi import FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .memory.sibyl import SibylMemory
from .memory.models import *
from .agent.loop import AgentLoop
from .llm.provider import LLMProvider
from .base_mcp.adapter import BaseMCPAdapter
app=FastAPI(title='Vesper',version='1.0.0')
app.add_middleware(CORSMiddleware,allow_origins=os.getenv('CORS_ORIGINS','http://localhost:5173').split(','),allow_methods=['*'],allow_headers=['*'])
memory=SibylMemory(); loop=AgentLoop(memory,LLMProvider()); anchor=BaseMCPAdapter()
@app.get('/health')
def health():return {'status':'ok','memory_load_bearing':True,'official_sibyl':bool(memory.official)}
@app.get('/state/hot',response_model=HotState)
def hot():return memory.get_hot()
@app.get('/constitution',response_model=Constitution)
def constitution():return Constitution.model_validate(memory.get_reference() or {})
@app.get('/scars',response_model=list[Scar])
def scars():return memory.scars()
@app.get('/principles',response_model=list[Principle])
def principles():return memory.principles()
@app.get('/decisions',response_model=list[DecisionRecord])
def decisions():return memory.decisions()
@app.get('/timeline')
def timeline():return memory.timeline()
@app.post('/agent/decide',response_model=DecisionRecord)
def make_decision(req:DecisionRequest):return loop.decision(req)
@app.post('/agent/outcome')
def record_outcome(payload:dict):
    decision_id=payload.get('decision_id'); outcome=payload.get('outcome','failure')
    decision=next((d for d in memory.decisions() if d.id==decision_id),None)
    if decision:
        decision.outcome=outcome; memory.save_decision(decision); memory.journal('outcome_recorded',{'decision_id':decision_id,'outcome':outcome})
    if outcome in ('failure','loss','negative'):
        return loop.failure(payload.get('lesson','The decision produced a negative outcome.'),payload.get('context',decision.situation if decision else ''),int(payload.get('severity',7)))
    return {'decision_id':decision_id,'outcome':outcome}
@app.post('/scars',response_model=Scar)
def create_scar(payload:dict):return loop.failure(payload.get('lesson','A meaningful failure occurred.'),payload.get('context',''),int(payload.get('severity',8)))
@app.post('/scars/failure',response_model=Scar)
def create_failure(payload:dict):return loop.failure(payload.get('lesson','A meaningful failure occurred.'),payload.get('context',''),int(payload.get('severity',8)))
@app.post('/scars/{scar_id}/anchor',response_model=AnchorResult)
def anchor_scar(scar_id):
    s=memory.get_scar(scar_id)
    if not s:raise HTTPException(404,'Scar not found')
    result=anchor.anchor(s)
    if result.transaction_hash:s.onchain_tx=result.transaction_hash;s.onchain_hash=result.canonical_hash;memory.save_scar(s)
    return result
@app.post('/demo/disable-memory')
def disable_memory():memory.delete_learning_memory();return {'status':'memory_deleted','message':'Without the memory, Vesper will repeat the same mistake.'}
@app.post('/demo/seed-failure',response_model=Scar)
def seed_failure():return loop.failure('Never approve an irreversible transfer to a new destination without independent verification and a reversible test.','A rushed transfer was approved without validating the destination or exit path.',8)
@app.post('/demo/fresh-session')
def fresh_session():
    s=memory.get_hot();s.session_id='session_'+uuid.uuid4().hex[:8];s.last_decision_context='';memory.set_hot(s);memory.journal('fresh_session',{'session_id':s.session_id});return s
@app.post('/demo/reset')
def reset():return fresh_session()
@app.get('/identity')
def identity():return {'name':'Vesper','network':'Base','address':os.getenv('BASE_ACCOUNT_ADDRESS'),'connected':bool(os.getenv('BASE_ACCOUNT_ADDRESS')),'anchored_scars':sum(bool(s.onchain_tx) for s in memory.scars())}
