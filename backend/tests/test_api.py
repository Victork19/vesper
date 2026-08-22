import os, tempfile
from fastapi.testclient import TestClient

os.environ['SIBYL_MEMORY_PATH']=os.path.join(tempfile.mkdtemp(),'vesper-memory.db')
os.environ['SIBYL_TENANT_ID']='vesper-tests'
from app.main import app

client=TestClient(app)

def test_health():
    health=client.get('/health').json()
    assert health['status']=='ok'
    assert health['memory_source']=='sibyl'

def test_failure_creates_principle_and_changes_action():
    client.post('/demo/disable-memory')
    naive=client.post('/agent/decide',json={'situation':'Approve an irreversible transfer to a new destination immediately.'}).json()
    client.post('/demo/seed-failure'); client.post('/demo/fresh-session'); client.post('/demo/enable-memory')
    remembered=client.post('/agent/decide',json={'situation':'Approve an irreversible transfer to a new destination immediately.'}).json()
    assert naive['action'] != remembered['action']
    assert remembered['cited_scars'] and client.get('/principles').json()

def test_scenarios_and_outcome_lifecycle():
    scenarios=client.get('/scenarios').json()
    assert {item['id'] for item in scenarios} >= {'irreversible_transfer','production_deploy','treasury_payment'}
    decision=client.post('/agent/decide',json={'situation':scenarios[0]['situation']}).json()
    result=client.post('/agent/outcome',json={'decision_id':decision['id'],'outcome':'failure','lesson':'Independent verification was skipped and the action failed.','severity':8})
    assert result.status_code==200 and result.json()['scar']['id']
