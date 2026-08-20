# Vesper

Vesper is a long-horizon decision agent whose memory is load-bearing. It stores meaningful failures as permanent scars, turns them into rules/cooldowns/trust changes, and cites those scars in later decisions.

## Judge path: verify the gate in under two minutes

1. Open the live site. The chrome shows `Memory ON`, the scar count, trust, cooldowns, Base status, and the GitHub link.
2. Click `Disable memory`. The status must become `MEMORY DISABLED`.
3. Click `Run same decision` for the prefilled irreversible-transfer situation. This is the naive baseline and should show `No scars recalled`.
4. Click `Create scar`, then `Enable memory`.
5. Click `Run same decision` again without changing the situation. The decision now cites the scar and should become safer (`DO NOTHING` or `REFUSE / REQUEST MORE EVIDENCE`). The UI records both outcomes side by side.
6. On the scar, click `Anchor on Base`. The UI only shows a Basescan link after the configured Base action returns a confirmed transaction hash.

This is the continuous deletion beat to record: same situation, memory off, baseline decision, scar write, memory on, same decision, visible citation.

## What to inspect

| Proof | Location |
| --- | --- |
| Memory deletion | `backend/app/memory/sibyl.py`, `POST /demo/disable-memory` |
| Memory-off behavior | `backend/app/agent/loop.py`, `HotState.memory_enabled` |
| Scar write/read | `backend/app/agent/scars.py`, `backend/app/memory/sibyl.py` |
| Decision citation | `backend/app/agent/decision.py`, `DecisionRecord.cited_scars` |
| Tiered persistence | `SibylMemory`: HOT, WARM, COLD, REFERENCE, ARCHIVE |
| Base anchor | `contracts/ScarAnchor.sol`, `backend/app/base_mcp/adapter.py`, `POST /scars/{id}/anchor` |
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

The backend uses the Sibyl client when available and keeps a local SQLite mirror for a reproducible offline demo. The deletion endpoint removes learning memory and explicitly switches recall off; it does not silently claim that memory still exists.

## Base proof

Base is a proof anchor, not the primary memory store. `contracts/ScarAnchor.sol` emits `ScarAnchored(bytes32 scarHash, string scarId, ...)`. Configure the approved mainnet flow in the backend environment and set `BASE_DEMO_TX_HASH` only to a real confirmed Base transaction hash. Never use a placeholder hash in the submission.

The UI links confirmed anchors directly to `https://basescan.org/tx/<hash>` and displays the number of anchored scars from `/identity`.

## API

FastAPI docs: `/docs`

Core endpoints: `/agent/decide`, `/scars`, `/scars/{id}/anchor`, `/decisions`, `/state/hot`, `/identity`, `/health`, `/demo/disable-memory`, `/demo/seed-failure`, `/demo/enable-memory`, and `/demo/fresh-session`.

## Submission checklist

- Record the deletion test continuously with the same situation and both outcomes visible.
- Show the commit or timestamp during the recording.
- Show a real confirmed Base mainnet transaction in the scar card and open its Basescan link.
- Keep the video focused on memory deletion, scar creation, decision change, and proof.
