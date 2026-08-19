import json, os, urllib.request
from ..memory.models import AnchorResult

class BaseMCPClient:
    """Thin remote MCP JSON-RPC boundary. OAuth token is supplied by the operator; no keys are stored."""
    def __init__(self): self.url=os.getenv('BASE_MCP_URL','https://mcp.base.org'); self.token=os.getenv('BASE_MCP_ACCESS_TOKEN')
    def call(self, method, params):
        if not self.token: return None
        body=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode()
        req=urllib.request.Request(self.url,body,{'Content-Type':'application/json','Authorization':'Bearer '+self.token})
        with urllib.request.urlopen(req,timeout=20) as res: return json.loads(res.read())
    def prepare_anchor(self, scar):
        result=self.call('tools/call',{'name':os.getenv('BASE_MCP_ANCHOR_TOOL','send_transaction'),'arguments':{'to':os.getenv('BASE_ANCHOR_CONTRACT',''),'data':'0x','value':'0'}})
        if result and result.get('result'):
            text=json.dumps(result['result'])
            return {'status':'pending_approval','approval_url':next((x for x in text.split('"') if x.startswith('http')),None),'request_id':result.get('id')}
        return {'status':'not_connected','approval_url':None,'request_id':None}
