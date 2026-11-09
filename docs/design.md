# WebSocket Basics: Group Chat Room (Design)

Date: 2026-11-09

## 1. Why this project

This is the first WebSocket project. The goal is **strong basics**, not a feature-rich app.

The long-term goal is a live team board, like a Jira board: everyone on a team opens the same page, the team lead drags a card from Pending to In Progress to Done, and everyone sees it move right away, with no refresh and no polling. That board is **not** built today. Today we build the smallest app that teaches every idea the board will need, and we lay out the project in a way that can be reused as a **template** for later WebSocket projects.

The app is a **group chat room**. Chat is used because it is small and still covers every basic: connecting, sending and receiving, broadcasting to everyone, an agreed message format, join and leave, catching up a newcomer, and surviving dropped connections. Later, "chat message" becomes "card moved" and "catch-up history" becomes "the current board".

## 2. How we work

- **The learner writes all the code and runs every command.** They create every folder and file, starting from the empty folder.
- Claude guides: for each step, what to create, why it is shaped that way, and the key code. On tricky parts, Claude gives hints before full code.
- After each step the learner runs it, checks it works, and Claude reviews what they wrote before moving on.
- One level at a time. Stop after each level for questions.
- **The learner knows the concepts** (asyncio, `async`/`await`, React `useEffect`) **but hasn't written this code by hand before.** So the async parts (Levels 1 and 2: the endpoint loop, the manager's broadcast) and the hook parts (Level 4 and especially Level 6: `useEffect` cleanup, `useRef`, timers) are split into small mini-steps. Each mini-step adds a few lines, explains each line, and is run before the next.

### Learning records

Kept inside the project folder, same as the learner's earlier project:
- `command.txt` (project root): every command run, in order, with a one-line comment on what it was for. The learner adds to it as they go.
- `learning/level-N-<name>.md`: a short note per level covering what was built, the ideas it taught, the one subtle part, and a **"The code worth reading"** table (file, what to look at, why). Claude's call: Claude drafts each note at the end of the level, since it's a summary rather than code, and the learner reads and corrects it.

## 3. Goals, non-goals, anti-goals

**Goals**
- Understand the WebSocket lifecycle: handshake, open, messages, close, errors.
- Build the standard server pattern: a connection manager that tracks who is connected and broadcasts.
- Define a typed message protocol, mirrored on the backend (Pydantic) and the frontend (TypeScript).
- Handle join/leave, catch-up for newcomers, and reconnects after a drop.
- Have a clean folder layout, settings kept separate from code, and tests for the WebSocket endpoint.

**Non-goals (later projects)**
- User accounts, login, or permissions.
- A database. Messages live in server memory and are lost on restart.
- Multiple chat rooms.
- Running more than one server process. (The in-memory manager only knows the connections on its own process. Scaling out needs something like Redis pub/sub. That's a lesson for the board project.)
- Deployment.

**Anti-goals (would make this a failure even if it works)**
- Claude writing the learner's code for them.
- Libraries that hide WebSockets, such as Socket.IO. We use FastAPI's built-in WebSocket support and the browser's built-in `WebSocket`.
- Overbuilding: features, abstractions, or styling that get in the way of the basics.

## 4. Stack (decided by the learner)

| Part | Choice |
|---|---|
| Backend | Python 3.12, **FastAPI**, run with **uvicorn**, project managed by **uv** |
| Frontend | **React + TypeScript**, using **bun** as runtime and package manager |
| WebSocket | FastAPI's built-in `WebSocket` on the server, the browser's native `WebSocket` on the client |
| Tests | pytest with FastAPI's `TestClient` (it can open WebSocket connections in tests) |

Claude's calls (not discussed): `pydantic-settings` for settings, and bun's own React template (`bun init --react`), the same one used in the learner's previous project. Vite is a fine alternative if the template gets in the way.

## 5. Folder structure (the template)

```text
Websockets_Basics/
├── README.md                  how to run backend, frontend, tests
├── .gitignore
├── command.txt                every command run, in order
├── learning/                  one note per level
├── docs/
│   └── design.md              this file
├── backend/
│   ├── pyproject.toml         created by uv
│   ├── .env.example           settings with safe example values
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            creates the FastAPI app, adds CORS, includes routers, /health route
│   │   ├── config.py          settings: allowed origins, history size
│   │   └── chat/
│   │       ├── __init__.py
│   │       ├── chat.py        the WebSocket endpoint: /ws
│   │       ├── manager.py     ConnectionManager: connect, disconnect, broadcast, history
│   │       └── schemas.py     the message protocol as Pydantic models
│   └── tests/
│       └── test_chat_ws.py
└── frontend/
    ├── package.json           created by bun
    └── src/
        ├── App.tsx
        ├── types/messages.ts      the same protocol as TypeScript types
        ├── hooks/useChatSocket.ts all WebSocket code lives here, nowhere else
        └── components/
            ├── JoinForm.tsx
            ├── ConnectionStatus.tsx
            ├── OnlineCount.tsx
            ├── MessageList.tsx
            └── MessageInput.tsx
```

The rules that make it a reusable template:
1. **Endpoint, manager, and protocol are separate files.** The endpoint handles one connection; the manager knows about all of them; the protocol says what messages mean.
2. **The protocol is defined once per side**, and the two sides match.
3. **All browser WebSocket code is in one hook.** Components only see state (messages, online count, connection status) and functions (`join`, `sendChat`).

## 6. The message protocol

Every message is JSON with a `type` field.

**Browser to server**

| type | fields | meaning |
|---|---|---|
| `join` | `name` | First message after connecting: "this is who I am" |
| `chat` | `text` | Send a chat message |
| `ping` | none | "Are you still there?" (heartbeat) |

**Server to browser**

| type | fields | meaning |
|---|---|---|
| `welcome` | `history` (last N chat messages), `online` | Reply to `join`: catch up the newcomer |
| `chat` | `name`, `text`, `sent_at` | A chat message, sent to everyone |
| `user_joined` | `name`, `online` | Someone joined |
| `user_left` | `name`, `online` | Someone left or dropped |
| `pong` | none | Reply to `ping` |
| `error` | `message` | The last message was invalid; the connection stays open |

Rules:
- The server validates every incoming message against the protocol. An invalid message gets an `error` reply, not a crash.
- A `chat` sent before `join` gets an `error`.
- The server fills in `name` and `sent_at` on chat messages. It never trusts the browser for those.

## 7. The six levels

Each level ends with something the learner can see working.

| Level | What gets built | The basic it teaches | Done when |
|---|---|---|---|
| 0. Setup | Folders, git, uv backend with a `/health` route, bun React app | Project layout, the template | Both servers start; `/health` answers |
| 1. Echo | `/ws` sends back whatever it receives (plain text). Tried first from the browser's DevTools console with `new WebSocket(...)`, then from a bare React page | Handshake, open/message/close events, `accept`, `receive_text`, `send_text`, `WebSocketDisconnect` | A message typed in the browser comes back |
| 2. Broadcast | `ConnectionManager` keeps a list of connections; every message goes to everyone | Server-side connection tracking, cleaning up on disconnect | Two tabs see each other's messages |
| 3. Message types | Switch to JSON; Pydantic models on the server, TS types in the browser; `error` replies | A message protocol and validation | Bad JSON gets an `error`, and the connection survives |
| 4. Join and leave | `join` with a name, `user_joined`/`user_left`, online count, the real UI components | The connection lifecycle as app events | Opening and closing tabs updates everyone's online count |
| 5. Catch-up | Server keeps the last N messages (N from settings); `welcome` carries them | Sending current state to a newcomer | A new tab sees recent messages straight away |
| 6. Survive drops | Browser reconnects with growing waits (1s, 2s, 4s, up to a cap) and re-sends `join`; `ping`/`pong` heartbeat; connection status shown | Reconnecting, heartbeats, why connections die quietly | Stop the server, start it again, and the page reconnects by itself |

Tests grow with the levels: echo, broadcast between two test clients, invalid message gets `error`, join/leave counts, and history on `welcome`.

### Level 6 details (Claude's calls)

- **Two kinds of heartbeat, one per side.**
  - Server side: uvicorn already sends low-level WebSocket ping frames and closes connections that stop answering (its `ws_ping_interval` / `ws_ping_timeout` settings, 20 s by default). A dead client then shows up in our code as a normal `WebSocketDisconnect`, so the manager removes it and broadcasts `user_left`. We write no server-side timer; we explain this setting and try it.
  - Browser side: browsers can't send low-level pings from JavaScript, so the hook sends our app-level `{"type": "ping"}` every 25 s. If no `pong` arrives within 10 s, it closes the socket and starts reconnecting.
- **On reconnect, replace the message list** with the `welcome` history. Don't merge it, or messages show up twice when the server didn't restart.

### Other small rules (Claude's calls)

- Duplicate names are allowed; names are trimmed, 1 to 30 characters.
- A second `join` on the same connection gets an `error`.
- The frontend reads the backend's WebSocket URL from an environment variable, with `ws://localhost:8000/ws` as the default.

## 8. Standard practices included (kept small)

- **Settings from the environment** (`config.py` + `.env.example`): allowed origins, history size.
- **Origin check on the WebSocket.** Browsers don't apply CORS to WebSockets, so the endpoint checks the `Origin` header against the allowed list and refuses others. This is a real security basic that tutorials often skip. It's added in **Level 3**, after the DevTools console experiments in Levels 1 and 2, so those aren't blocked. Connections with **no** `Origin` header (tests, command-line tools) are allowed: the check exists to stop other websites from using a visitor's browser, and only browsers send `Origin`. (Claude's call.)
- **Validate input** with Pydantic; never trust the browser for identity or timestamps.
- **Always clean up** on disconnect, including unexpected ones, so the manager never holds dead connections.
- **Cap message size** (for example 1,000 characters for chat text) so one client can't flood everyone.

## 9. Left to the builder

- Exact component styling. Keep it plain; basic CSS is enough.
- Ports. Backend on 8000 and frontend on bun's default are the expected choices, but change them if they're taken.
- Exact package versions. Use current releases at build time.
