# Vesper

Vesper is a scar-bound long-horizon agent for the Sibyl Memory Hackathon. Its operational scars are load-bearing: active WARM scars become constraints in every decision, while decisions and failure events are append-only COLD journal entries.

Before publishing this repository, copy `.env.example` to `backend/.env` locally and keep all credentials out of Git. See [SECURITY.md](SECURITY.md).

## Run locally

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Or run the backend with `docker compose -f backend/docker-compose.yml up --build`.

The demo buttons exercise disable-memory → inject-failure → reset → decision. Set `BASE_ACCOUNT_ADDRESS` and, after operator approval through the Base MCP flow, `BASE_DEMO_TX_HASH` to display a real Base proof. The adapter computes a canonical scar hash and is intentionally approval-safe by default.

## EC2 + Cloudflare Pages

Copy `deploy/ec2.env.example` to `backend/.env`, set the production values, then run `bash deploy/deploy.sh`. Put Nginx/Caddy and TLS in front of port 8000; do not expose the application port publicly. For Cloudflare Pages use `frontend` as the root directory, `npm run build` as the build command, `dist` as the output directory, and set `VITE_API_URL` to the HTTPS API domain.

Sibyl is enabled by default when `sibyl-memory-client` is installed. Run `sibyl init` on the EC2 host before first launch if you want an activated account; unactivated local mode stays offline. Base MCP is OAuth-based: configure the access token obtained from the official Base MCP authorization flow, then surface the returned approval URL to the operator. Base MCP never receives Vesper's private key; writes remain user-approved.

## Verification

```bash
cd backend
pytest -q
curl http://localhost:8000/health
```

## API

FastAPI docs are available at `http://localhost:8000/docs`. The required endpoints include `/agent/decide`, `/scars`, `/scars/{id}/anchor`, `/decisions`, `/state/hot`, `/identity`, and `/health`, plus demo helpers.
