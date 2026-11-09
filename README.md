# WebSocket Basics: Group Chat Room

A small group chat that covers every WebSocket basic: connecting, broadcasting, a typed JSON protocol, join and leave, catching up newcomers, and surviving dropped connections. It's laid out as a template for later WebSocket projects.

- Design: [docs/design.md](docs/design.md)
- Build plan, level by level: [docs/plan.md](docs/plan.md)
- Every command run: [commands.txt](commands.txt)

## Run it

**Backend** (FastAPI, port 8000):

```bash
cd backend
uv run uvicorn app.main:app --reload --port 8000 --ws-ping-interval 20 --ws-ping-timeout 20
```

**Frontend** (React + bun, port 3000). `--hot` makes it pick up code changes without a restart:

```bash
cd frontend
bun --hot src/index.ts
```

Open http://localhost:3000 in two tabs, join with two names, and chat.

**Tests:**

```bash
cd backend
uv run pytest -v
```

## Settings

`backend/.env` (copy it from `.env.example`):

| Setting | Default | Meaning |
|---|---|---|
| `ALLOWED_ORIGINS` | `["http://localhost:3000"]` | Web pages allowed to open a WebSocket to the server (JSON list) |
| `HISTORY_SIZE` | `20` | How many recent messages a newcomer gets |

## How dead connections are detected (Level 6)

A connection can die **quietly**: Wi-Fi drops, a laptop sleeps, or a router forgets the connection. Neither side gets a "closed" event straight away, so each side checks on the other.

| Side | How | Settings |
|---|---|---|
| **Server** | uvicorn sends low-level WebSocket *ping frames*. A client that doesn't answer is closed, and our code sees a normal `WebSocketDisconnect`, so the user is removed and everyone gets `user_left`. No code of ours does this. | `--ws-ping-interval 20 --ws-ping-timeout 20` (seconds; these are uvicorn's defaults, written out so they're visible) |
| **Browser** | JavaScript can't send ping frames, so the hook sends our own `{"type": "ping"}` every 25 s. With no `pong` within 10 s, it drops the socket and reconnects. | `PING_INTERVAL_MS`, `PONG_TIMEOUT_MS` in `frontend/src/hooks/useChatSocket.ts` |

**Reconnecting:** after a drop, the browser waits 1 s, 2 s, 4 s, 8 s, then 10 s between attempts, and re-joins under the same name. The server's `welcome` then replaces the message list, so nothing shows twice. History lives in server memory, so it's empty after a server restart.
