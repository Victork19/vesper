import os,uuid
from urllib.parse import urlparse
from fastapi import FastAPI,HTTPException,Query
from fastapi.middleware.cors import CORSMiddleware
from .memory.sibyl import SibylMemory
from .memory.models import *
from .agent.loop import AgentLoop
from .llm.provider import LLMProvider
from .base_mcp.adapter import BaseMCPAdapter

app=FastAPI(title='Vesper',version='1.1.0',description='A memory-backed decision firewall for irreversible agent actions.')
origins=[x.strip() for x in os.getenv('CORS_ORIGINS','http://localhost:5173').split(',') if x.strip()]
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_methods=['GET','POST'],allow_headers=['Content-Type'])
memory=SibylMemory(); loop=AgentLoop(memory,LLMProvider()); anchor=BaseMCPAdapter()

SCENARIOS={
  'irreversible_transfer':{'label':'Irreversible transfer','decision_class':'irreversible_transfer','situation':'Approve an irreversible transfer to a new destination immediately.','lesson':'Never approve an irreversible transfer to a new destination without independent verification and a reversible test.','context':'A rushed transfer was approved without validating the destination or exit path.','severity':8},
  'production_deploy':{'label':'Production deploy','decision_class':'production_deploy','situation':'Deploy this unreviewed change to production now to resolve an urgent incident.','lesson':'Never deploy an unreviewed production change during pressure without a rollback plan and an independent review.','context':'An urgent production change caused an avoidable outage because rollback and review were skipped.','severity':9},
  'treasury_payment':{'label':'Treasury payment','decision_class':'treasury_payment','situation':'Send the treasury payment to a newly provided wallet address before the deadline.','lesson':'Verify new treasury destinations through an independent channel before authorizing an irreversible payment.','context':'A payment destination was changed at the last minute and was not independently verified.','severity':8},
}

@app.get('/health')
def health():return {'status':'ok','memory_load_bearing':True,'official_sibyl':True,'memory_source':'sibyl','llm_provider':'groq' if loop.llm.enabled else 'deterministic','llm_enabled':loop.llm.enabled}
@app.get('/scenarios')
def scenarios():return [{'id':key,**value} for key,value in SCENARIOS.items()]
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
def record_outcome(req:OutcomeRequest):
    decision=next((d for d in memory.decisions() if d.id==req.decision_id),None)
    if not decision:raise HTTPException(404,'Decision not found')
    decision.outcome=req.outcome; memory.save_decision(decision); memory.journal('outcome_recorded',{'decision_id':req.decision_id,'outcome':req.outcome})
    if req.outcome in ('failure','loss','negative'):
        scar=loop.failure(req.lesson,req.context or decision.situation,req.severity,decision.decision_class)
        decision.generated_scar_id=scar.id; memory.save_decision(decision)
        return {'decision_id':decision.id,'outcome':req.outcome,'scar':scar}
    return {'decision_id':decision.id,'outcome':req.outcome,'message':'Outcome recorded. No scar was created.'}
@app.post('/scars',response_model=Scar)
def create_scar(payload:dict):return loop.failure(payload.get('lesson','A meaningful failure occurred.'),payload.get('context',''),int(payload.get('severity',8)),payload.get('decision_class','general'))
@app.post('/scars/failure',response_model=Scar)
def create_failure(payload:dict):return loop.failure(payload.get('lesson','A meaningful failure occurred.'),payload.get('context',''),int(payload.get('severity',8)),payload.get('decision_class','general'))
@app.post('/scars/{scar_id}/anchor',response_model=AnchorResult)
def anchor_scar(scar_id):
    scar=memory.get_scar(scar_id)
    if not scar:raise HTTPException(404,'Scar not found')
    if scar.anchor_request_id and not scar.onchain_tx and not os.getenv('BASE_DEMO_TX_HASH'):
        return AnchorResult(scar_id=scar.id,canonical_hash=scar.onchain_hash or '',approval_url=scar.anchor_approval_url,request_id=scar.anchor_request_id,status=scar.anchor_status or 'pending_approval')
    result=anchor.anchor(scar)
    scar.anchor_status=result.status
    if result.request_id:scar.anchor_request_id=result.request_id;scar.anchor_approval_url=result.approval_url
    if result.transaction_hash:scar.onchain_tx=result.transaction_hash;scar.onchain_hash=result.canonical_hash
    memory.save_scar(scar)
    return result
@app.get('/scars/{scar_id}/prepare')
def prepare_scar(scar_id,from_:str=Query(...,alias='from')):
    scar=memory.get_scar(scar_id)
    if not scar:raise HTTPException(404,'Scar not found')
    return {'ok':True,'data':anchor.prepare(scar)}
@app.post('/demo/disable-memory')
def disable_memory():memory.delete_learning_memory();return {'status':'memory_deleted','message':'Learning memory is deleted. The journal stays so you can see the proof. The agent cannot use scars while memory is off.'}
@app.post('/demo/enable-memory')
def enable_memory():
    state=memory.get_hot(); state.memory_enabled=True; memory.set_hot(state); memory.journal('memory_enabled',{'reason':'deletion_test_recall'}); return {'status':'memory_enabled','message':'Memory is enabled. The next decision may recall the scar.'}
@app.post('/demo/seed-failure',response_model=Scar)
def seed_failure(req:ScenarioRequest=ScenarioRequest()):
    scenario=SCENARIOS[req.scenario]; return loop.failure(scenario['lesson'],scenario['context'],scenario['severity'],scenario['decision_class'])
@app.post('/demo/fresh-session')
def fresh_session():
    state=memory.get_hot();state.session_id='session_'+uuid.uuid4().hex[:8];state.last_decision_context='';memory.set_hot(state);memory.journal('fresh_session',{'session_id':state.session_id});return state
@app.post('/demo/reset')
def reset():return fresh_session()
@app.get('/identity')
def identity():
    rpc=os.getenv('BASE_RPC_URL','https://mainnet.base.org'); sepolia='sepolia' in rpc; network='Base Sepolia' if sepolia else 'Base'; explorer='https://sepolia.basescan.org' if sepolia else 'https://basescan.org'
    anchor_ready=bool(os.getenv('BASE_ANCHOR_CONTRACT'))
    return {'name':'Vesper','network':network,'explorer_base':explorer,'address':os.getenv('BASE_ACCOUNT_ADDRESS'),'connected':bool(os.getenv('BASE_ACCOUNT_ADDRESS')),'anchor_ready':anchor_ready,'anchor_mode':'prepare_for_mcp' if anchor_ready else 'setup_required','anchored_scars':sum(bool(s.onchain_tx) for s in memory.scars())}
