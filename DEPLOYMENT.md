# Vesper Deployment and Submission Runbook

This guide covers the production backend, Cloudflare Pages frontend, Sibyl
Memory, Base anchor verification, and the judge-proof demo.

## Architecture

- `frontend/`: Vite/React app deployed to Cloudflare Pages.
- `backend/`: FastAPI service, normally deployed with Docker on a host with a
  persistent `/app/data` volume.
- Sibyl Memory: the only memory layer used by Vesper.
- Base MCP: execution layer for approved `send_calls` transactions. Vesper never stores a private key.

## Secrets and repository hygiene

Never commit API keys, wallet keys, MCP tokens, Sibyl credentials, `.env`
files, or local memory files. Configure secrets only on the backend host or in
the deployment provider.

## Backend environment

Start from `backend/.env.example`. A production setup should include:

```env
CORS_ORIGINS=https://YOUR_PROJECT.pages.dev
SIBYL_MEMORY_PATH=/app/data/sibyl-memory.db
SIBYL_TENANT_ID=vesper
```

For the competition deployment, also configure Base mainnet:

```env
BASE_RPC_URL=https://mainnet.base.org
BASE_MCP_URL=https://mcp.base.org
BASE_MCP_ANCHOR_TOOL=send_calls
BASE_ANCHOR_CONTRACT=0xYOUR_DEPLOYED_MAINNET_SCAR_ANCHOR
```

Use a real deployed `ScarAnchor` address. Never put wallet private keys in the
repository or Vesper's environment. The recommended demo path uses Claude,
Cursor, or Codex as the MCP host and calls Vesper's prepare endpoint; Vesper
does not require a Base MCP access token.

For optional LLM assistance, configure one provider:

```env
GROQ_API_KEY=...
GROQ_MODEL=llama-3.3-70b-versatile
```

The deterministic safety policy remains active even when an LLM is enabled.

## Docker deployment

From the repository root:

```bash
cp backend/.env.example backend/.env
# edit backend/.env
docker compose -f backend/docker-compose.yml up -d --build
docker compose -f backend/docker-compose.yml ps
curl http://127.0.0.1:8000/health
```

The health response must report:

```json
{
  "official_sibyl": true,
  "memory_source": "sibyl"
}
```

If Sibyl is unavailable, the backend fails fast rather than silently running a
different memory implementation.

Persist the Docker volume containing `/app/data`. Without it, the agent loses
its local Sibyl database and cannot recall prior scars after a restart.

### Enable HTTPS before opening the production frontend

The checked-in `deploy/nginx.conf` is the temporary HTTP configuration used to
complete the Let's Encrypt challenge. It is not the final production
configuration. On the EC2 security group, allow inbound TCP 80 and 443 and do
not expose port 8000 publicly. From the repository root on EC2, start the
backend and HTTP Nginx:

```bash
docker compose -f backend/docker-compose.yml up -d --build backend nginx
```

Issue the certificate through the running HTTP challenge endpoint:

```bash
docker compose -f backend/docker-compose.yml run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d vesper-scar.duckdns.org \
  --email YOUR_LETSENCRYPT_EMAIL \
  --agree-tos --no-eff-email
```

After Certbot succeeds, activate the TLS configuration and recreate Nginx:

```bash
cp deploy/nginx-https.conf deploy/nginx.conf
docker compose -f backend/docker-compose.yml up -d --force-recreate nginx
docker compose -f backend/docker-compose.yml exec nginx nginx -t
curl --fail https://vesper-scar.duckdns.org/health
```

Do not point Cloudflare Pages or the Base Account SDK at the backend until the
last HTTPS check succeeds. Renew the certificate before expiry, then recreate
Nginx so it reloads the renewed files.

## Base network configuration

The anchor verifier checks `eth_getTransactionReceipt` and only displays a
confirmed transaction when the receipt succeeded. Configure the RPC and the
contract for the same network.

### Base Sepolia testing

```env
BASE_RPC_URL=https://sepolia.base.org
BASE_ANCHOR_CONTRACT=0xYOUR_SEPOLIA_SCAR_ANCHOR
BASE_DEMO_TX_HASH=0xYOUR_SUCCESSFUL_SEPOLIA_TRANSACTION
```

### Base mainnet submission proof

```env
BASE_RPC_URL=https://mainnet.base.org
BASE_ANCHOR_CONTRACT=0xYOUR_MAINNET_SCAR_ANCHOR
BASE_DEMO_TX_HASH=0xYOUR_SUCCESSFUL_MAINNET_TRANSACTION
```

For the competition deployment, use Base mainnet: chain ID `8453`, RPC
`https://mainnet.base.org`, and `https://basescan.org`. Deploy
`contracts/ScarAnchor.sol` to Base mainnet, set the resulting contract address,
and verify the contract/source on Basescan before the demo. Do not use a
placeholder hash. `BASE_DEMO_TX_HASH` is optional and only verifies a real
MCP-submitted transaction; it is not the execution path.

The Base Account flow is: the frontend calls `wallet_connect` for Base mainnet →
`GET /scars/{id}/prepare?from=0x...` → the frontend's Base Account provider calls
`wallet_sendCalls` with the returned `{to,value,data}`
on chain `0x2105` → user approval in Base Account → frontend polls
`wallet_getCallsStatus` → `POST /scars/{id}/verify` with the resulting transaction
hash → Vesper verifies the receipt and `ScarAnchored` event. The same prepared
call can be submitted by a connected Base MCP host with `send_calls`; the host
owns its own authentication and approval UI.

```env
BASE_MCP_URL=https://mcp.base.org
BASE_MCP_ANCHOR_TOOL=send_calls
BASE_ACCOUNT_ADDRESS=0xYOUR_OPERATOR_ADDRESS
BASE_ANCHOR_CONTRACT=0xYOUR_CONTRACT
```

The MCP host owns the Base MCP connection and the Base Account approval. No Base
MCP token is configured in Vesper for this flow. The browser flow uses the
official Base Account SDK loaded in `frontend/index.html`.

### Credentials and account roles

These values are different and must not be confused:

- `BASE_ANCHOR_CONTRACT` is the public address of the deployed `ScarAnchor`
  contract. A contract has no private key.
- `BASE_ACCOUNT_ADDRESS` is the public address of the Base Account that will
  approve and submit the anchor call. It is not a private key and is safe to
  expose as an address.
- The private key or signing authority for the Base Account stays inside Base
  Account/the MCP host. Vesper must never receive or store it.
- Base MCP credentials are managed by the MCP host. Vesper does not need a
  Base MCP access token for the recommended Claude, Cursor, or Codex flow.

For contract deployment, use Foundry with the deployer's signer. The deployer
address may also be the Base Account address, but it does not have to be. After
deployment, put only the resulting contract address in
`BASE_ANCHOR_CONTRACT`.

### Deploy ScarAnchor to Base mainnet with Forge

Install Foundry and keep the deployer key in Foundry's account/keychain or an
ephemeral shell secret. From the repository root:

```bash
export BASE_MAINNET_RPC_URL=https://mainnet.base.org
export DEPLOYER_PRIVATE_KEY=0xYOUR_DEPLOYER_PRIVATE_KEY

cast wallet address --private-key "$DEPLOYER_PRIVATE_KEY"
cast balance "$(cast wallet address --private-key "$DEPLOYER_PRIVATE_KEY")" \
  --rpc-url "$BASE_MAINNET_RPC_URL"

forge create contracts/ScarAnchor.sol:ScarAnchor \
  --rpc-url "$BASE_MAINNET_RPC_URL" \
  --private-key "$DEPLOYER_PRIVATE_KEY" \
  --broadcast
```

Record Forge's `Deployed to:` address. That is the value for
`BASE_ANCHOR_CONTRACT`; it is not a private key. Remove the shell secret:

```bash
unset DEPLOYER_PRIVATE_KEY
```

Check that bytecode exists on Base mainnet:

```bash
cast code 0xYOUR_MAINNET_SCAR_ANCHOR --rpc-url "$BASE_MAINNET_RPC_URL"
```

Set the deployed address in the backend environment, rebuild/restart the
backend, and confirm `/identity` reports `Base`. Verify the source on Basescan
separately with `forge verify-contract`, keeping the Basescan API key outside
the repository.

### Restarting the backend for the fresh-session proof

Restart means stopping the API process and starting it again while preserving
the Sibyl data volume. It proves that the scar survives a process boundary.

For Docker deployment, from the repository root:

```bash
docker compose -f backend/docker-compose.yml restart backend
curl --fail http://127.0.0.1:8000/health
```

For a stronger explicit stop/start sequence:

```bash
docker compose -f backend/docker-compose.yml stop backend
docker compose -f backend/docker-compose.yml up -d backend
curl --fail http://127.0.0.1:8000/health
```

Do not remove the `vesper-data` volume. Removing it destroys the local Sibyl
database and invalidates the persistence demonstration.

For local development, press `Ctrl+C` in the terminal running Uvicorn, then
start it again:

```bash
cd backend
SIBYL_MEMORY_PATH=./data/dev-memory.db SIBYL_TENANT_ID=vesper-dev uvicorn app.main:app --reload
```

After restarting, leave the browser open, run the exact same situation, and
confirm that the returned decision cites the persisted scar.

The recommended submission sequence is `get_wallets` ->
`GET /scars/{id}/prepare?from=0x...` -> Base MCP `send_calls` -> user approval
in Base Account -> `get_request_status` -> Vesper receipt and
`ScarAnchored` event verification. The confirmed mainnet transaction must be
visible from the scar card during the recording.

### Mainnet preflight

Run these checks from the deployed host before recording:

```bash
curl --fail https://YOUR_BACKEND_HOST/health
curl --fail https://YOUR_BACKEND_HOST/identity
curl --fail -X POST https://YOUR_BACKEND_HOST/demo/fresh-session
```

Confirm `/identity` reports `Base`, the configured mainnet contract is present,
the frontend `VITE_API_URL` is not localhost, and backend `CORS_ORIGINS`
contains the exact production Pages origin. After creating a scar, call
`/scars/{id}/prepare?from=0x...` and confirm `chainId` is `8453`, `value` is
`0x0`, and `to` is the deployed mainnet contract.

## Cloudflare Pages

Use these settings when connecting the repository:

```text
Root directory: frontend
Build command: npm run build
Build output directory: dist
```

Set:

```text
VITE_API_URL=https://YOUR_BACKEND_HOST
VITE_GITHUB_URL=https://github.com/Victork19/vesper
```

Set the exact Pages origin in backend `CORS_ORIGINS`, then restart the backend.

## Local development

Backend:

```bash
cd backend
python -m venv .venv
# activate .venv
pip install -r requirements-dev.txt
SIBYL_MEMORY_PATH=./data/dev-memory.db SIBYL_TENANT_ID=vesper-dev uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Run checks:

```bash
cd backend
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m compileall -q app
```

The test suite must pass before recording. If the host does not have Docker or
the development Python dependencies installed, run these checks inside the
backend image or install `requirements-dev.txt` in a dedicated virtual
environment; a missing test runner is not a passing result.

## Fresh-session proof

The strongest demo is a real backend restart, not just a UI reset:

1. Start with memory enabled and no scar.
2. Disable memory and run the irreversible-transfer situation.
3. Create the scar and enable memory.
4. Stop and restart the backend process while keeping the data volume.
5. Run the exact same situation without changing the text.
6. Show the changed action, cited scar ID, rule, cooldown, and trust score.
7. Anchor the scar and show the verified Basescan receipt.

Keep the browser recording continuous around the recall moment and show the
health endpoint or commit hash on screen. The README maps the critical calls
for judges: Sibyl writes/reads are in `backend/app/memory/sibyl.py`, decision
recall is in `backend/app/agent/loop.py`, and the UI proof is in
`frontend/src/main.tsx`.

## Hackathon submission checklist

- Public repository with the root MIT license.
- README explains what Vesper persists, recalls, and changes.
- 2–5 minute demo with a fresh-session recall moment.
- Real Base transaction shown on the matching explorer.
- Two public posts: the demo and at least one build log.
- Tag `@sibylcap` and every claimed partner stack.
- No secrets, placeholder hashes, or unverified claims.
