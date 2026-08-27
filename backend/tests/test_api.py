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
    assert remembered['decision_class']=='irreversible_transfer'
    assert remembered['situation_id']=='irreversible_transfer'

def test_decision_class_recalls_different_phrasing():
    client.post('/demo/disable-memory')
    client.post('/demo/seed-failure',json={'scenario':'irreversible_transfer'})
    client.post('/demo/enable-memory')
    decision=client.post('/agent/decide',json={'situation':'Authorize a rushed wallet destination transfer now.'}).json()
    assert decision['decision_class']=='irreversible_transfer'
    assert decision['cited_scars']

def test_severity_nine_forces_do_nothing():
    client.post('/demo/disable-memory')
    scar=client.post('/scars',json={'lesson':'A critical production release failed without rollback.','context':'production deploy','severity':9,'decision_class':'production_deploy'}).json()
    client.post('/demo/enable-memory')
    decision=client.post('/agent/decide',json={'situation':'Deploy an urgent production release now.'}).json()
    assert scar['decision_class']=='production_deploy'
    assert decision['action']=='DO NOTHING'
    assert scar['id'] in decision['cited_scars']

def test_prepare_returns_base_send_calls_payload():
    scar=client.post('/scars',json={'lesson':'Verify the destination before an irreversible transfer.','severity':8,'decision_class':'irreversible_transfer'}).json()
    response=client.get(f"/scars/{scar['id']}/prepare?from=0x0000000000000000000000000000000000000001")
    assert response.status_code==200
    body=response.json()
    assert body['ok'] is True
    assert set(body['data'])=={'to','value','data','chainId'}
    assert body['data']['value']=='0x0' and body['data']['chainId']==8453
    assert body['data']['data'].startswith('0x') and len(body['data']['data'])>10

def test_scenarios_and_outcome_lifecycle():
    scenarios=client.get('/scenarios').json()
    assert {item['id'] for item in scenarios} >= {'irreversible_transfer','production_deploy','treasury_payment'}
    decision=client.post('/agent/decide',json={'situation':scenarios[0]['situation']}).json()
    result=client.post('/agent/outcome',json={'decision_id':decision['id'],'outcome':'failure','lesson':'Independent verification was skipped and the action failed.','severity':8})
    assert result.status_code==200 and result.json()['scar']['id']
