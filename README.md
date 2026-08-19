# Vesper

Vesper is a long-horizon decision agent for the Sibyl Memory Hackathon.

Every meaningful failure is stored as a permanent scar. Scars change the agent's future decisions. In a fresh session, Vesper recalls the scars and behaves differently. Without the memory, it repeats the same mistakes. Memory is load-bearing.

## Run locally

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

### First-time Sibyl setup

Install the free local client and sign in once:

```bash
pip install 'sibyl-memory-cli[mcp]'
sibyl init
```

The browser sign-in may use an email code or wallet. Credentials are saved locally in `~/.sibyl-memory/credentials.json`. After this one-time setup, Vesper uses the free five-tier local memory on disk. No paid Sibyl API key is required for the core demo.

## Memory walkthrough

1. Disable memory and run the transfer decision. Vesper proposes a risky action.
2. Inject a failure. The failure is persisted as a permanent scar with a timestamp.
3. Start a fresh session and run the same decision.
4. Vesper recalls the scar, tightens its rules, lowers trust, and chooses a safer action or does nothing.

Scars are stored as WARM records, current trust and cooldown data are stored as HOT state, and decisions/events are written to the COLD journal. The backend writes through the Sibyl client when it is available; the local SQLite adapter keeps the same structure for offline development.

## Deployment

The backend runs on EC2 with Docker Compose. The frontend runs on Cloudflare Pages.

For Cloudflare Pages:

```text
Root directory: frontend
Build command: npm run build
Output directory: dist
VITE_API_URL=https://api.example.com
```

For EC2, copy `deploy/ec2.env.example` to `backend/.env`, configure the API domain and CORS, then run:

```bash
bash deploy/deploy.sh
```

Keep credentials out of Git. See [SECURITY.md](SECURITY.md).

## Base proof

High-severity scars can be anchored through the user-approved Base MCP flow. The Base contract is in `contracts/ScarAnchor.sol`. Base is used for proof only; Sibyl Memory remains the primary store.

## API

FastAPI documentation is available at `/docs`. Main endpoints include `/agent/decide`, `/scars`, `/scars/{id}/anchor`, `/decisions`, `/state/hot`, `/identity`, and `/health`.
