import os
os.environ['SIBYL_OFFICIAL']='0'; os.environ['SIBYL_DB_PATH']='./data/test-vesper.db'
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def test_health(): assert client.get('/health').json()['status']=='ok'
def test_failure_creates_principle_and_changes_action():
    client.post('/demo/disable-memory')
    naive=client.post('/agent/decide',json={'situation':'Approve an irreversible transfer to a new destination immediately.'}).json()
    client.post('/demo/seed-failure'); client.post('/demo/fresh-session')
    remembered=client.post('/agent/decide',json={'situation':'Approve an irreversible transfer to a new destination immediately.'}).json()
    assert naive['action'] != remembered['action']
    assert remembered['cited_scars'] and client.get('/principles').json()
