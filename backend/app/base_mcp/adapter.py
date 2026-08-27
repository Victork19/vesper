import hashlib, json, os, re, urllib.request
from ..memory.models import AnchorResult

TX_RE=re.compile(r'^0x[a-fA-F0-9]{64}$')

class BaseMCPAdapter:
    @staticmethod
    def _explorer(tx):
        host='sepolia.basescan.org' if 'sepolia' in os.getenv('BASE_RPC_URL','') else 'basescan.org'
        return f'https://{host}/tx/{tx}'
    def _canonical_hash(self,scar):
        canonical=json.dumps(scar.model_dump(exclude={'onchain_tx','onchain_hash'}),sort_keys=True,separators=(',',':')).encode()
        try:
            from eth_hash.auto import keccak
            return '0x'+keccak(canonical).hex()
        except ImportError:
            return '0x'+hashlib.sha3_256(canonical).hexdigest()
    def _receipt(self,tx,scar_hash):
        if not TX_RE.match(tx):return None
        body=json.dumps({'jsonrpc':'2.0','id':1,'method':'eth_getTransactionReceipt','params':[tx]}).encode()
        req=urllib.request.Request(os.getenv('BASE_RPC_URL','https://mainnet.base.org'),body,{'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=10) as res:
            result=json.loads(res.read()).get('result')
        if not result or result.get('status')!='0x1' or not result.get('blockNumber'):return None
        contract=os.getenv('BASE_ANCHOR_CONTRACT','').lower()
        try:
            from eth_hash.auto import keccak
            event_topic='0x'+keccak(b'ScarAnchored(bytes32,string,uint256,address)').hex()
        except ImportError:return None
        matching=[log for log in result.get('logs',[]) if (not contract or (log.get('address') or '').lower()==contract) and log.get('topics',[None])[0]==event_topic and len(log.get('topics',[]))>1 and log['topics'][1].lower()==scar_hash.lower()]
        if not matching:return None
        return result
    def _calldata(self,scar,digest=None):
        digest=digest or self._canonical_hash(scar)
        from eth_hash.auto import keccak
        from eth_abi import encode
        return '0x'+(keccak(b'anchor(bytes32,string)')[:4]+encode(['bytes32','string'],[bytes.fromhex(digest[2:]),scar.id])).hex()
    def prepare(self,scar):
        return {'to':os.getenv('BASE_ANCHOR_CONTRACT',''),'value':'0x0','data':self._calldata(scar),'chainId':8453}
    def anchor(self,scar):
        digest=self._canonical_hash(scar); tx=os.getenv('BASE_DEMO_TX_HASH')
        if tx:
            try:
                receipt=self._receipt(tx,digest)
                if receipt:
                    return AnchorResult(scar_id=scar.id,canonical_hash=digest,transaction_hash=tx,explorer_url=self._explorer(tx),status='confirmed')
            except Exception: pass
            return AnchorResult(scar_id=scar.id,canonical_hash=digest,status='awaiting_chain_verification')
        return AnchorResult(scar_id=scar.id,canonical_hash=digest,status='awaiting_mcp_transaction')
