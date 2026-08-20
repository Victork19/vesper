import hashlib, json, os
from ..memory.models import AnchorResult
from .client import BaseMCPClient

class BaseMCPAdapter:
    def anchor(self, scar):
        canonical = json.dumps(scar.model_dump(exclude={'onchain_tx','onchain_hash'}), sort_keys=True, separators=(',',':')).encode()
        try:
            from eth_hash.auto import keccak
            digest = '0x' + keccak(canonical).hex()
        except ImportError:
            digest = '0x' + hashlib.sha3_256(canonical).hexdigest()
        tx = os.getenv('BASE_DEMO_TX_HASH')
        if not tx and os.getenv('BASE_MCP_ACCESS_TOKEN'):
            from eth_hash.auto import keccak
            from eth_abi import encode
            calldata='0x'+(keccak(b'anchor(bytes32,string)')[:4]+encode(['bytes32','string'],[bytes.fromhex(digest[2:]),scar.id])).hex()
            pending=BaseMCPClient().prepare_anchor(scar,calldata)
            return AnchorResult(scar_id=scar.id, canonical_hash=digest, approval_url=pending.get('approval_url'), request_id=pending.get('request_id'), status=pending['status'])
        return AnchorResult(scar_id=scar.id, canonical_hash=digest, transaction_hash=tx, explorer_url=f'https://basescan.org/tx/{tx}' if tx else None, status='confirmed' if tx else 'awaiting_wallet_approval')
