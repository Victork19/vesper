# Vesper

Vesper is a decision firewall for autonomous agents. It turns consequential
failures into durable memory, recalls that memory before the next decision, and
can anchor the resulting scar on Base as independently verifiable proof.

The product is built around one question:

> When an agent has already failed this way, what should stop it from doing the
> same thing again?

Vesper answers with a persistent scar, a safer decision, and a trace that can
survive a fresh session.

## The proof in five steps

The main demo uses the same situation throughout:

1. Disable learning memory. Active scars are deleted from recall and the UI
   shows `MEMORY DISABLED`.
2. Run the decision once. This is the memory-off baseline and should produce
   the naive action.
3. Record a failure. Vesper writes the lesson to Sibyl as a scar.
4. Enable memory again.
5. Run a fresh-session decision with the same situation. The agent should cite
   the scar and choose a safer action, such as refusing or requesting more
   evidence.

The important comparison is not a static before-and-after screenshot. It is
the same decision with memory off and then with persisted memory recalled.

## How Vesper works

```text
decision request
      |
      v
recall scars and principles ---> safety gate ---> action
      ^                                      |
      |                                      v
  Sibyl memory <--- failure / outcome <--- result
      |
      v
optional Base proof of the scar
```

The backend uses the official `sibyl-memory-client` as its memory layer. Vesper
maps its memory model into Sibyl tiers:

| Tier | Role |
| --- | --- |
| HOT | Current memory state, trust, constraints, and cooldowns |
| WARM | Active scars and consolidated principles |
| COLD | Decision and event journal |
| REFERENCE | Constitution and hard limits |
| ARCHIVE | Retained records outside active recall |

Deleting learning memory is explicit: the learning records are removed, the
journal remains for auditability, and recall stays disabled until memory is
enabled again.

## Base anchoring

Base is the proof layer, not Vesper's memory store. Vesper prepares a
`ScarAnchor.anchor()` transaction; a user-controlled signer approves it. Vesper
never holds a private key.

The UI intentionally has one action:

```text
Anchor this scar on Base
[ Anchor on Base ]
```

After clicking it, the user chooses a signer:

- **Wallet** — the default path, using Reown AppKit for MetaMask, OKX, Rabby,
  and other supported wallets.
- **Base Account** — the optional MCP / Base App path using `wallet_sendCalls`.

Both paths use the same backend flow:

1. `GET /scars/{id}/prepare?from=connectedAddress`
2. The selected signer submits `ScarAnchor.anchor()` on Base mainnet.
3. `POST /scars/{id}/verify` receives the transaction hash.
4. Vesper verifies the receipt and `ScarAnchored` event before showing one
   Basescan link.

Configure a real deployed `ScarAnchor` address in `BASE_ANCHOR_CONTRACT`.
`BASE_RPC_URL` must point to Base mainnet and the address must contain deployed
bytecode. A Reown project ID is separate: it configures the frontend wallet
modal and does not make the backend anchor ready.

For a previously confirmed demo transaction, set `BASE_DEMO_TX_HASH` to its
public Base transaction hash. On the next `/identity` request Vesper verifies
the receipt and event against the current scar before saving it, so the verified
anchor count and Basescan link remain connected to the demo. Set
`BASE_DEMO_SCAR_ID` when the hash belongs to a specific scar. Never use a hash
that was not produced by the configured `ScarAnchor` contract.

## Repository map

| Area | Location |
| --- | --- |
| FastAPI application | `backend/app/main.py` |
| Sibyl memory adapter | `backend/app/memory/sibyl.py` |
| Decision and recall loop | `backend/app/agent/loop.py` |
| Base preparation and verification | `backend/app/base_mcp/adapter.py` |
| Anchor contract | `contracts/ScarAnchor.sol` |
| React/Vite frontend | `frontend/src/main.tsx` |
| Frontend styling | `frontend/src/styles.css` |
| Docker deployment | `backend/docker-compose.yml` |

## Run locally

Prerequisites: Python 3.11+, Node.js, and npm.

### 1. Configure the backend

From the repository root:

```bash
cp backend/.env.example backend/.env
```

Set at least these values for Base anchoring:

```env
CORS_ORIGINS=http://localhost:5173
BASE_RPC_URL=https://mainnet.base.org
BASE_ANCHOR_CONTRACT=0xYOUR_DEPLOYED_MAINNET_SCAR_ANCHOR
SIBYL_MEMORY_PATH=./data/sibyl-memory.db
SIBYL_TENANT_ID=vesper
```

`BASE_ANCHOR_CONTRACT` must be the deployed `ScarAnchor` contract, not a wallet
or Base Account address. Never commit `.env` files, private keys, API keys, or
memory databases.

Start the API:

```bash
cd backend
python -m venv .venv
# activate .venv using your platform's command
pip install -r requirements.txt
uvicorn app.main:app --reload --env-file .env
```

If you run Uvicorn without `--env-file`, export the variables in the shell
first. Docker Compose loads `backend/.env` automatically.

### 2. Configure the frontend

In another terminal:

```bash
cp frontend/.env.example frontend/.env
```

Set the API URL and a Reown project ID:

```env
VITE_API_URL=http://localhost:8000
VITE_REOWN_PROJECT_ID=your-reown-project-id
```

Create the project in the [Reown Dashboard](https://dashboard.reown.com/) and
add the deployed frontend origin to its allowlist. The wallet connection uses
Reown; the frontend does not use a separate browser-injected wallet provider.

Start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, usually `http://localhost:5173`.

## API surface

FastAPI's interactive documentation is available at `/docs`.

Core endpoints:

```text
GET  /health
GET  /identity
GET  /scenarios
GET  /scars
GET  /principles
GET  /decisions
GET  /state/hot
POST /agent/decide
POST /agent/outcome
GET  /scars/{id}/prepare
POST /scars/{id}/anchor       # MCP / server-side path
POST /scars/{id}/verify       # wallet and Base Account verification
POST /demo/disable-memory
POST /demo/enable-memory
POST /demo/seed-failure
POST /demo/fresh-session
```

For a configured Base deployment, `/identity` should report:

```json
{
  "network": "Base",
  "anchor_ready": true
}
```

If `anchor_ready` is false, check the backend process environment, the RPC
chain ID, and whether `BASE_ANCHOR_CONTRACT` has deployed bytecode on Base
mainnet. The readiness check intentionally fails closed.

## Checks

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest -q
python -m compileall -q app
```

Build the frontend with:

```bash
cd frontend
npm ci
npm run build
```

## Deployment

The supported layout is a Dockerized FastAPI backend with persistent storage
and a Cloudflare Pages frontend. See [DEPLOYMENT.md](DEPLOYMENT.md) for the
production runbook, CORS configuration, HTTPS proxy, persistent Sibyl data,
and Base verification checklist.

The backend must be restarted or recreated after changing its environment.
The frontend must be rebuilt after changing `VITE_API_URL` or
`VITE_REOWN_PROJECT_ID`, because Vite embeds those values at build time.

## Project status

Vesper was built for the Sibyl Labs Hackathon. It uses the official
`sibyl-memory-client` package and the open-source Base contract and MCP
interfaces documented in this repository. The scars, principles, decision
lifecycle, UI, and proof workflow are original to this project.
