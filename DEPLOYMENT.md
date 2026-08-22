# Vesper Deployment and Submission Runbook

This guide covers the production backend, Cloudflare Pages frontend, Sibyl
Memory, Base anchor verification, and the judge-proof demo.

## Architecture

- `frontend/`: Vite/React app deployed to Cloudflare Pages.
- `backend/`: FastAPI service, normally deployed with Docker on a host with a
  persistent `/app/data` volume.
- Sibyl Memory: the only memory layer used by Vesper.
- Base: optional proof anchor. Vesper never stores a private key.

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

Do not use a placeholder hash. Confirm the transaction on the matching
Basescan network before recording the demo. The current hackathon rules require
an executed Base action for the Base partner multiplier, but do not explicitly
state whether Sepolia qualifies, so mainnet is the safest submission proof.

If using the MCP approval path instead of `BASE_DEMO_TX_HASH`, configure:

```env
BASE_MCP_URL=https://mcp.base.org
BASE_MCP_ACCESS_TOKEN=...
BASE_MCP_ANCHOR_TOOL=send_transaction
BASE_ACCOUNT_ADDRESS=0xYOUR_OPERATOR_ADDRESS
BASE_ANCHOR_CONTRACT=0xYOUR_CONTRACT
```

Keep the access token server-side. Approve the transaction, then verify its
receipt on the matching Basescan network.

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
python -m pytest -q
python -m compileall -q app
```

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
