# Vesper

Vesper is a decision firewall for autonomous agents handling irreversible actions. It stores meaningful failures as permanent scars, turns them into rules, cooldowns, and trust changes, and cites those scars before the agent repeats a risky decision.

The problem is simple: autonomous systems can act faster than they can learn. Vesper gives them durable operational memory. A transfer, production deploy, or treasury payment that fails once becomes a constraint on what happens next.

## Judge path: verify the gate in under two minutes

1. Open the live site. The chrome shows memory state, scar count, trust, cooldowns, network, and Base proof status.
2. Click `Disable memory`. The status must become `MEMORY DISABLED`.
3. Choose a failure class: irreversible transfer, production deploy, or treasury payment.
4. Click `Run same decision` for the selected situation. This is the naive baseline and should show `No scars recalled`.
5. Record the outcome or use `Create scar`, then `Enable memory`.
6. Restart the backend while keeping the Sibyl memory path, then run the exact same situation again. The decision now cites the scar and should become safer (`DO NOTHING` or `REFUSE / REQUEST MORE EVIDENCE`).
7. On the scar, click `Anchor on Base`. The UI only shows a network-correct explorer link after the exact `ScarAnchored` event and scar hash are verified.

This is the continuous deletion beat to record: same situation, memory off, baseline decision, scar write, memory on, same decision, visible citation.

## What to inspect

| Proof | Location |
| --- | --- |
| Memory deletion | `backend/app/memory/sibyl.py`, `POST /demo/disable-memory` |
| Memory-off behavior | `backend/app/agent/loop.py`, `HotState.memory_enabled` |
| Scar write/read | `backend/app/agent/scars.py`, `backend/app/memory/sibyl.py` |
| Decision citation | `backend/app/agent/decision.py`, `DecisionRecord.cited_scars` |
| Tiered persistence | `SibylMemory`: HOT, WARM, COLD, REFERENCE, ARCHIVE |
| Base anchor | `contracts/ScarAnchor.sol`, `backend/app/base_mcp/adapter.py`, `GET /scars/{id}/prepare`, `POST /scars/{id}/anchor` |
| Frontend proof | `frontend/src/main.tsx` |

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

The frontend defaults to `http://localhost:8000`. For deployment set `VITE_API_URL` and optionally `VITE_GITHUB_URL`.

## Memory architecture

- HOT: trust, memory-enabled state, active constraints, and cooldowns.
- WARM: scars and consolidated principles.
- COLD: immutable decision/event journal.
- REFERENCE: constitution and hard limits.
- ARCHIVE: retained records removed from active recall.

The backend uses the official Sibyl client as its only memory layer. The deletion endpoint removes learning memory and explicitly switches recall off; it does not silently claim that memory still exists.

## Base proof

Base is a proof anchor, not the primary memory store. Vesper prepares `ScarAnchor`
calldata at `GET /scars/{id}/prepare` and never holds a key. The UI has one
`Anchor on Base` action: the default Wallet path opens Reown AppKit for MetaMask,
OKX, Rabby, and other supported wallets, then submits the returned EIP-1193
provider transaction. Base Account remains the optional MCP / Base App path using
`wallet_sendCalls` and approval. Both paths submit the resulting hash to
`POST /scars/{id}/verify`. Vesper only marks an anchor confirmed after checking the
receipt and matching `ScarAnchored(scarHash, scarId)`, then links it to the correct
Base explorer. `contracts/ScarAnchor.sol` emits
`ScarAnchored(bytes32 scarHash, string scarId, ...)`. Keep `BASE_DEMO_TX_HASH` only
as a verifier after a real MCP transaction; never use a placeholder hash.

Set `VITE_REOWN_PROJECT_ID` in the frontend deployment from a project created in
the [Reown Dashboard](https://dashboard.reown.com/). Configure the deployed site
origin in that project as well.

## API

FastAPI docs: `/docs`

Core endpoints: `/agent/decide`, `/agent/outcome`, `/scenarios`, `/scars`, `/scars/{id}/prepare`, `/scars/{id}/anchor`, `/scars/{id}/verify`, `/decisions`, `/state/hot`, `/identity`, `/health`, `/demo/disable-memory`, `/demo/seed-failure`, `/demo/enable-memory`, and `/demo/fresh-session`.

## Submission checklist

- Record the deletion test continuously with the same situation and both outcomes visible.
- Show the commit or timestamp during the recording.
- Show a real confirmed Base mainnet transaction in the scar card and open its Basescan link.
- Show a real backend restart and fresh-session recall.
- Include a short Prior Work declaration and two public build posts.
- Keep the video focused on the decision firewall: failure, memory, changed action, and proof.

## Memory implementation note

Production uses `sibyl-memory-client` as the only store. `SibylMemory` maps
Vesper's tiers to Sibyl entities, state documents, reference documents, and
journal events. Decision recall reads from Sibyl WARM entities and COLD
events; `/demo/disable-memory` deletes learning entities in Sibyl and leaves
only the explicit disabled HOT state.

The strongest proof is a fresh backend process: create the scar, stop and
restart the API, then run the same situation. The decision must cite the scar
and change its action. The health endpoint exposes `memory_source`,
`official_sibyl`, and `llm_enabled` so the recording can prove which path is
running.

## Development checks

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest -q
python -m compileall -q app
```

Base anchors are only displayed as confirmed after a successful Base RPC
receipt check. Set `BASE_RPC_URL` and `BASE_ANCHOR_CONTRACT` in deployment;
never use a placeholder transaction hash.

## Product-market focus

Vesper is designed for autonomous-agent operators, crypto treasury teams, DAO
multisig operators, and production teams that approve irreversible actions.
The initial wedge is a decision firewall: Vesper sits between an agent's
proposal and execution, requiring stronger evidence when the agent's own
history says a class of action has failed before.

## Prior Work declaration

Vesper was built for the Sibyl Labs Hackathon. It uses the official
`sibyl-memory-client` package and the open-source Base contract and MCP
interfaces documented in this repository. No Sibyl reference build was copied
as the product; Vesper's scars, principles, decision lifecycle, UI, and proof
workflow are original to this project.
