import os
os.environ['SIBYL_OFFICIAL']='0'; os.environ['SIBYL_DB_PATH']='./data/test-vesper.db'
from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)
def test_health(): assert client.get('/health').json()['status']=='ok'
def test_demo_memory_changes_decision():
    client.post('/demo/reset'); client.post('/demo/failure')
    r=client.post('/agent/decide',json={'situation':'Approve an irreversible transfer to a new destination immediately.'})
    assert r.status_code==200 and r.json()['cited_scars']
