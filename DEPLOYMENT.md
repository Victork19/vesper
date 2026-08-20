# Vesper Deployment

This guide deploys the backend to EC2 and the Vite frontend to Cloudflare Pages.

## 1. Repository and secrets

Push the repository to GitHub. Keep credentials out of Git: API keys, wallet keys, Base MCP tokens, Sibyl credentials, `.env` files, and SQLite databases.

## 2. EC2

Use Ubuntu 22.04 or newer with an Elastic IP. Point `vesper-scar.duckdns.org` to the EC2 Elastic IP. Allow only SSH from your IP, and ports 80 and 443 publicly. Do not expose port 8000 publicly.

Install Docker and DNS tools. Nginx runs inside Docker, so a host Nginx service is not required:

```bash
sudo apt update
sudo apt install -y ca-certificates curl git dnsutils
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER"
newgrp docker
```

Clone and configure:

```bash
git clone https://github.com/Victork19/vesper.git
cd vesper
cp deploy/ec2.env.example backend/.env
nano backend/.env
```

Set at least:

```env
CORS_ORIGINS=https://vesper-scar.pages.dev
SIBYL_OFFICIAL=1
SIBYL_DB_PATH=/app/data/vesper.db
GROQ_API_KEY=your_key
```

For Base proof anchoring, also set `BASE_ACCOUNT_ADDRESS`, `BASE_MCP_ACCESS_TOKEN`, and `BASE_ANCHOR_CONTRACT`. Never place a private key in the environment.

## 3. Deploy and connect the Base MCP

Base anchoring is an operator-approved MCP transaction. Vesper does not hold a private key. The backend sends an `anchor(bytes32,string)` call to the deployed `ScarAnchor` contract through the configured Base MCP, then stores the confirmed transaction hash on the scar.

### 3.1 Deploy the anchor contract on Base mainnet

Use a funded deployer wallet and deploy [contracts/ScarAnchor.sol](contracts/ScarAnchor.sol) to Base mainnet (chain ID `8453`). The contract address returned by the deployment is `BASE_ANCHOR_CONTRACT`.

With Foundry, after installing and configuring your deployer signer:

```bash
export BASE_RPC_URL=https://mainnet.base.org
export BASE_DEPLOYER=0xYOUR_DEPLOYER_ADDRESS
forge create contracts/ScarAnchor.sol:ScarAnchor \
  --rpc-url "$BASE_RPC_URL" \
  --account YOUR_FOUNDRY_ACCOUNT \
  --broadcast
```

Record the deployed address and verify the contract on Basescan if desired. Do not use a testnet address for the submission demo.

### 3.2 Configure the MCP connection

Add the MCP values to `backend/.env` on EC2:

```env
BASE_MCP_URL=https://mcp.base.org
BASE_MCP_ACCESS_TOKEN=your_operator_token
BASE_MCP_ANCHOR_TOOL=send_transaction
BASE_ANCHOR_CONTRACT=0xYOUR_BASE_MAINNET_SCAR_ANCHOR
BASE_ACCOUNT_ADDRESS=0xYOUR_OPERATOR_ADDRESS
```

The configured MCP must support the JSON-RPC `tools/call` method with the `send_transaction` tool. The request sent by Vesper contains the contract address, ABI-encoded calldata, and `value: 0`; the MCP/operator is responsible for approval and signing. Keep the access token in the server-side `.env` only.

Restart the backend after changing the environment:

```bash
docker compose -f backend/docker-compose.yml up -d --build backend
docker compose -f backend/docker-compose.yml logs --tail=100 backend
```

### 3.3 Exercise and verify one real anchor

Create a scar, request its anchor, approve the pending MCP request, then verify the transaction:

```bash
API=https://vesper-scar.duckdns.org
SCAR_ID=$(curl -s -X POST "$API/demo/seed-failure" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
curl -s -X POST "$API/scars/$SCAR_ID/anchor"
curl -s "$API/scars" | python3 -m json.tool
```

The anchor response may first be `pending_approval` with an approval URL. After approval, repeat the anchor request or refresh the scar until it contains `onchain_tx`. Open `https://basescan.org/tx/<onchain_tx>` and confirm the transaction is on Base mainnet. The Vesper UI then shows `Base tx confirmed` and links directly to Basescan.

For local UI-only work, `BASE_DEMO_TX_HASH` can display a previously confirmed transaction, but never use a placeholder or testnet hash in the hackathon demo. Leave it unset when exercising the live MCP flow.

## 4. Sibyl Memory

For first-time setup on Ubuntu, install Python tooling first:

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv
python3 -m venv ~/.venvs/sibyl
source ~/.venvs/sibyl/bin/activate
python -m pip install --upgrade pip
python -m pip install 'sibyl-memory-cli[mcp]'
sibyl init
sibyl status
```

The browser sign-in may use an email code or wallet. Credentials are saved in `~/.sibyl-memory/credentials.json`. After this one-time setup, normal local reads and writes do not require a paid Sibyl API key. The Docker Compose file mounts this directory read-only into the backend container. The container stores its local database at `/app/data/vesper.db` through the Docker volume. For offline development, use `SIBYL_OFFICIAL=0`; the local mirror preserves the same memory tiers and deletion test.

## 5. Start the backend

```bash
docker compose -f backend/docker-compose.yml up -d --build
docker compose -f backend/docker-compose.yml ps
curl http://127.0.0.1:8000/health
```

The API documentation is available at `/docs`.

## 6. DuckDNS and containerized Nginx

In DuckDNS, create a subdomain and set its IPv4 address to your EC2 Elastic IP:

```text
vesper-scar.duckdns.org → YOUR_EC2_ELASTIC_IP
```

Wait for DNS to resolve:

```bash
sudo apt install -y dnsutils
dig +short vesper-scar.duckdns.org
```

The result should be your EC2 Elastic IP.

The Compose stack includes Nginx and exposes ports 80 and 443. Do not install or enable a second host Nginx service. The initial configuration is HTTP-only so Certbot can validate the hostname.

Start the stack:

```bash
docker compose -f backend/docker-compose.yml up -d --build
```

Request the certificate through the included Certbot container:

```bash
docker compose -f backend/docker-compose.yml run --rm certbot certonly --webroot -w /var/www/certbot -d vesper-scar.duckdns.org --email YOUR_EMAIL --agree-tos --no-eff-email
```

Switch Nginx to the HTTPS configuration:

```bash
cp deploy/nginx-https.conf deploy/nginx.conf
docker compose -f backend/docker-compose.yml up -d nginx
```

Verify HTTPS:

```bash
curl https://vesper-scar.duckdns.org/health
```

## 7. Cloudflare Pages

Connect the GitHub repository in **Workers & Pages → Create application → Pages → Connect to Git**.

Use these build settings:

```text
Framework preset: Vite
Root directory: frontend
Build command: npm run build
Build output directory: dist
```

Add this environment variable:

```text
VITE_API_URL=https://vesper-scar.duckdns.org
```

Cloudflare builds only `frontend` and deploys `frontend/dist`. The backend remains on EC2.

## 8. CORS

After Cloudflare gives you the Pages domain, set:

```env
CORS_ORIGINS=https://YOUR_PROJECT.pages.dev
```

Restart the backend:

```bash
docker compose -f backend/docker-compose.yml up -d --build
```

## 9. Deletion test

Run this against the production API:

```bash
API=https://vesper-scar.duckdns.org
curl -X POST "$API/demo/disable-memory"
curl -X POST "$API/agent/decide" -H 'Content-Type: application/json' -d '{"situation":"Approve an irreversible transfer to a new destination immediately."}'
curl -X POST "$API/demo/seed-failure"
curl -X POST "$API/demo/enable-memory"
curl -X POST "$API/demo/fresh-session"
curl -X POST "$API/agent/decide" -H 'Content-Type: application/json' -d '{"situation":"Approve an irreversible transfer to a new destination immediately."}'
```

The first decision should be the naive baseline. The second should cite the persisted scar and normally choose `DO NOTHING`.

## 10. Winning demo

1. Show the empty scar list and current trust score.
2. Disable memory and run the irreversible-transfer decision.
3. Show the naive action.
4. Create a scar and show its timestamp, rule, and cooldown.
5. Start a fresh session.
6. Run the exact same decision.
7. Show the changed action, cited scar, and tightened rule.
8. Show the Sibyl memory record.
9. Approve the Base MCP request and show the Basescan proof.

## 11. Operations

```bash
docker compose -f backend/docker-compose.yml logs -f backend
docker compose -f backend/docker-compose.yml restart backend
git pull
docker compose -f backend/docker-compose.yml up -d --build
```

Back up the persistent Docker volume regularly. Check `SECURITY.md` before making the repository public.

## Troubleshooting

- `Failed to fetch`: verify `VITE_API_URL`, HTTPS, Nginx, and `CORS_ORIGINS`.
- Empty memory: verify the Docker volume and `SIBYL_DB_PATH=/app/data/vesper.db`.
- No Base proof: verify Base MCP authorization, `BASE_MCP_ACCESS_TOKEN`, and `BASE_ANCHOR_CONTRACT`; transaction approval is manual by design.
