# Vesper Deployment

This guide deploys the backend to EC2 and the Vite frontend to Cloudflare Pages.

## 1. Repository and secrets

Push the repository to GitHub. Keep credentials out of Git: API keys, wallet keys, Base MCP tokens, Sibyl credentials, `.env` files, and SQLite databases.

## 2. EC2

Use Ubuntu 22.04 or newer with an Elastic IP. Point `vesper-scar.duckdns.org` to the EC2 Elastic IP. Allow only SSH from your IP, and ports 80 and 443 publicly. Do not expose port 8000 publicly.

Install Docker and Nginx:

```bash
sudo apt update
sudo apt install -y ca-certificates curl git nginx
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
CORS_ORIGINS=https://YOUR_PROJECT.pages.dev
SIBYL_OFFICIAL=1
SIBYL_DB_PATH=/app/data/vesper.db
GROQ_API_KEY=your_key
```

For Base proof anchoring, also set `BASE_ACCOUNT_ADDRESS`, `BASE_MCP_ACCESS_TOKEN`, and `BASE_ANCHOR_CONTRACT`. Never place a private key in the environment.

## 3. Sibyl Memory

For first-time setup, install the free local client and sign in once:

```bash
python3 -m pip install 'sibyl-memory-cli[mcp]'
sibyl init
sibyl status
```

The browser sign-in may use an email code or wallet. Credentials are saved in `~/.sibyl-memory/credentials.json`. After this one-time setup, normal local reads and writes do not require a paid Sibyl API key. The container stores its local database at `/app/data/vesper.db` through the Docker volume. For offline development, use `SIBYL_OFFICIAL=0`; the local mirror preserves the same memory tiers and deletion test.

## 4. Start the backend

```bash
docker compose -f backend/docker-compose.yml up -d --build
docker compose -f backend/docker-compose.yml ps
curl http://127.0.0.1:8000/health
```

The API documentation is available at `/docs`.

## 5. DuckDNS, Nginx, and HTTPS

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

Copy the included config, replace `api.example.com` with your DuckDNS hostname, and enable it:

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/vesper-api
sudo nano /etc/nginx/sites-available/vesper-api
sudo ln -s /etc/nginx/sites-available/vesper-api /etc/nginx/sites-enabled/vesper-api
sudo nginx -t
sudo systemctl reload nginx
```

Create a DNS `A` record pointing `api.yourdomain.com` to the EC2 Elastic IP, then install HTTPS:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d vesper-scar.duckdns.org
curl https://vesper-scar.duckdns.org/health
```

## 6. Cloudflare Pages

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

## 7. CORS

After Cloudflare gives you the Pages domain, set:

```env
CORS_ORIGINS=https://YOUR_PROJECT.pages.dev
```

Restart the backend:

```bash
docker compose -f backend/docker-compose.yml up -d --build
```

## 8. Deletion test

Run this against the production API:

```bash
API=https://vesper-scar.duckdns.org
curl -X POST "$API/demo/disable-memory"
curl -X POST "$API/agent/decide" -H 'Content-Type: application/json' -d '{"situation":"Approve an irreversible transfer to a new destination immediately."}'
curl -X POST "$API/demo/seed-failure"
curl -X POST "$API/demo/fresh-session"
curl -X POST "$API/agent/decide" -H 'Content-Type: application/json' -d '{"situation":"Approve an irreversible transfer to a new destination immediately."}'
```

The first decision should be the naive baseline. The second should cite the persisted scar and normally choose `DO NOTHING`.

## 9. Winning demo

1. Show the empty scar list and current trust score.
2. Disable memory and run the irreversible-transfer decision.
3. Show the naive action.
4. Create a scar and show its timestamp, rule, and cooldown.
5. Start a fresh session.
6. Run the exact same decision.
7. Show the changed action, cited scar, and tightened rule.
8. Show the Sibyl memory record.
9. Approve the Base MCP request and show the Basescan proof.

## 10. Operations

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
