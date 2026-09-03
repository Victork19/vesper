import hashlib, json, os, re, urllib.error, urllib.request
from ..memory.models import AnchorResult

TX_RE=re.compile(r'^0x[a-fA-F0-9]{64}$')
ADDRESS_RE=re.compile(r'^0x[a-fA-F0-9]{40}$')

class BaseMCPAdapter:
    def readiness(self):
        rpc=os.getenv('BASE_RPC_URL','https://mainnet.base.org'); contract=os.getenv('BASE_ANCHOR_CONTRACT','')
        if not ADDRESS_RE.fullmatch(contract):return False,'BASE_ANCHOR_CONTRACT is missing or invalid.'
        try:
            def call(method,params=[]):
                body=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode()
                req=urllib.request.Request(rpc,body,{'Content-Type':'application/json'})
                with urllib.request.urlopen(req,timeout=4) as res:return json.loads(res.read()).get('result')
            if call('eth_chainId')!='0x2105':return False,'BASE_RPC_URL is not connected to Base mainnet.'
            if call('eth_getCode',[contract,'latest']) in (None,'0x','0x0'):return False,'BASE_ANCHOR_CONTRACT has no deployed bytecode on Base mainnet.'
            from eth_hash.auto import keccak
            getter='0x'+keccak(b'anchoredAt(bytes32)')[:4].hex()+'00'*32
            result=call('eth_call',[{'to':contract,'data':getter},'latest'])
            if not isinstance(result,str) or len(result)<66:return False,'BASE_ANCHOR_CONTRACT does not expose the ScarAnchor interface.'
            return True,''
        except urllib.error.HTTPError as exc:return False,f'Base RPC rejected the request ({exc.code}).'
        except (urllib.error.URLError,TimeoutError):return False,'Base RPC could not be reached.'
        except Exception:return False,'Base RPC readiness check failed.'
    def is_ready(self):
        return self.readiness()[0]
    @staticmethod
    def _explorer(tx):
        host='sepolia.basescan.org' if 'sepolia' in os.getenv('BASE_RPC_URL','') else 'basescan.org'
        return f'https://{host}/tx/{tx}'
    def _canonical_hash(self,scar):
        canonical=json.dumps({'id':scar.id,'type':scar.type,'severity':scar.severity,'lesson':scar.lesson,'principle':scar.principle,'context':scar.context,'decision_class':scar.decision_class,'created_at':scar.created_at,'cooldown_until':scar.cooldown_until,'impact':scar.impact.model_dump()},sort_keys=True,separators=(',',':')).encode()
        try:
            from eth_hash.auto import keccak
            return '0x'+keccak(canonical).hex()
        except ImportError:
            return '0x'+hashlib.sha3_256(canonical).hexdigest()
    def _receipt(self,tx,scar_hash,scar_id=None,operator=None):
        if not TX_RE.match(tx):return None
        body=json.dumps({'jsonrpc':'2.0','id':1,'method':'eth_getTransactionReceipt','params':[tx]}).encode()
        req=urllib.request.Request(os.getenv('BASE_RPC_URL','https://mainnet.base.org'),body,{'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=10) as res:
            result=json.loads(res.read()).get('result')
        if not result or result.get('status')!='0x1' or not result.get('blockNumber'):return None
        chain_body=json.dumps({'jsonrpc':'2.0','id':2,'method':'eth_chainId','params':[]}).encode()
        chain_req=urllib.request.Request(os.getenv('BASE_RPC_URL','https://mainnet.base.org'),chain_body,{'Content-Type':'application/json'})
        with urllib.request.urlopen(chain_req,timeout=10) as res:
            if json.loads(res.read()).get('result')!='0x2105':return None
        tx_body=json.dumps({'jsonrpc':'2.0','id':3,'method':'eth_getTransactionByHash','params':[tx]}).encode()
        tx_req=urllib.request.Request(os.getenv('BASE_RPC_URL','https://mainnet.base.org'),tx_body,{'Content-Type':'application/json'})
        with urllib.request.urlopen(tx_req,timeout=10) as res:
            tx_result=json.loads(res.read()).get('result')
        if not tx_result or (operator and (tx_result.get('from') or '').lower()!=operator.lower()):return None
        contract=os.getenv('BASE_ANCHOR_CONTRACT','').lower()
        if not contract:return None
        try:
            from eth_hash.auto import keccak
            event_topic='0x'+keccak(b'ScarAnchored(bytes32,string,uint256,address)').hex()
        except ImportError:return None
        matching=[log for log in result.get('logs',[]) if (log.get('address') or '').lower()==contract and log.get('topics',[None])[0]==event_topic and len(log.get('topics',[]))>2 and log['topics'][1].lower()==scar_hash.lower() and (not operator or log['topics'][2].lower().endswith(operator.lower()[2:]))]
        if scar_id:
            from eth_abi import decode
            matching=[log for log in matching if decode(['string','uint256'],bytes.fromhex((log.get('data') or '0x')[2:]))[0]==scar_id]
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
    def verify(self,scar,transaction_hash,operator_address):
        digest=self._canonical_hash(scar)
        receipt=self._receipt(transaction_hash,digest,scar.id,operator_address)
        if not receipt:
            return AnchorResult(scar_id=scar.id,canonical_hash=digest,status='verification_failed')
        return AnchorResult(scar_id=scar.id,canonical_hash=digest,transaction_hash=transaction_hash,explorer_url=self._explorer(transaction_hash),status='confirmed')
