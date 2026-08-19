import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .memory.sibyl import SibylMemory
from .memory.models import *
from .agent.loop import AgentLoop
from .base_mcp.adapter import BaseMCPAdapter
from .llm.provider import LLMProvider

app = FastAPI(title='Vesper API', version='1.1.0')
app.add_middleware(CORSMiddleware, allow_origins=os.getenv('CORS_ORIGINS','http://localhost:5173').split(','), allow_methods=['*'], allow_headers=['*'])
memory, adapter = SibylMemory(), BaseMCPAdapter(); agent = AgentLoop(memory, adapter, LLMProvider())

@app.get('/health')
def health(): return {'status':'ok','service':'vesper','memory':'local-sibyl-compatible'}
@app.get('/state/hot', response_model=HotState)
def hot(): return memory.get_hot()
@app.get('/scars', response_model=list[Scar])
def scars(): return memory.scars()
@app.get('/scars/{scar_id}', response_model=Scar)
def scar(scar_id):
    item=memory.get_scar(scar_id)
    if not item: raise HTTPException(404,'Scar not found')
    return item
@app.post('/scars', response_model=Scar)
def create_scar(s: Scar): return agent.create_scar(s.model_dump())
@app.post('/scars/{scar_id}/anchor', response_model=AnchorResult)
def anchor_scar(scar_id):
    s=memory.get_scar(scar_id)
    if not s: raise HTTPException(404,'Scar not found')
    result=adapter.anchor(s)
    if result.transaction_hash:
        s.onchain_tx=result.transaction_hash; s.onchain_hash=result.canonical_hash; memory.save_scar(s)
    return result
@app.post('/agent/decide', response_model=DecisionRecord)
def make_decision(req: DecisionRequest): return agent.decision(req.situation, req.execute)
@app.get('/decisions', response_model=list[DecisionRecord])
def decisions(): return memory.decisions()
@app.get('/identity', response_model=Identity)
def identity(): return Identity(address=os.getenv('BASE_ACCOUNT_ADDRESS'), connected=bool(os.getenv('BASE_ACCOUNT_ADDRESS')), anchored_scars=sum(bool(s.onchain_tx) for s in memory.scars()))
@app.post('/demo/disable-memory')
def disable_memory():
    state=memory.get_hot(); state.session_bridge='MEMORY_DISABLED'; memory.set_hot(state); memory.journal('demo_memory_disabled',{}); return state
@app.post('/demo/reset')
def reset():
    state=memory.get_hot(); state.session_bridge='Session reset. Memory reloaded.'; memory.set_hot(state); return state
@app.post('/demo/failure', response_model=Scar)
def failure():
    s=agent.create_scar({'type':'decision_failure','severity':8,'context':'A rushed irreversible transfer was approved without validating the destination or exit path.','lesson':'Never execute an irreversible transfer without independent destination verification and a reversible test.','impact':'Vesper must refuse high-risk transfers lacking evidence and require a small test first.'})
    # Prepare the Base anchor immediately; a real adapter would now pause for wallet approval.
    proof = adapter.anchor(s)
    if proof.transaction_hash:
        s.onchain_tx=proof.transaction_hash; s.onchain_hash=proof.canonical_hash; memory.save_scar(s)
    return s
