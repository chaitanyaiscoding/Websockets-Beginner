# WebSocket Chat Room: Build Plan

> **How this plan is used:** the learner builds every task by hand, typing every file and running every command. Claude guides one mini-step at a time, gives hints before full code on tricky parts, and reviews after each task. Steps use checkboxes (`- [ ]`) to track progress. This plan gives the decisions (files, names, signatures, tests, commands). **Function bodies are left for the learner to write.**

**Goal:** A group chat room that teaches every WebSocket basic, laid out as a reusable template for later projects (next: a live team board).

**Architecture:** A FastAPI app with one WebSocket endpoint (`/ws`). A `ConnectionManager` tracks connections, names and recent history, and broadcasts. A typed JSON protocol is defined in Pydantic on the server and mirrored in TypeScript. A React app keeps all socket code in one hook, `useChatSocket`.

**Tech Stack:** Python 3.12, FastAPI, uvicorn, pydantic-settings, pytest, uv · React + TypeScript, bun

**Spec:** `docs/design.md`

## Global Constraints

- The learner types all code and runs all commands. Every command goes into `command.txt` with a one-line comment, as it's run.
- No Socket.IO or other WebSocket wrapper libraries. Use FastAPI's `WebSocket` and the browser's `WebSocket`.
- No database, no auth, one room, one server process.
- Protocol: every message is JSON with a `type` field. Browser→server: `join`, `chat`, `ping`. Server→browser: `welcome`, `chat`, `user_joined`, `user_left`, `pong`, `error`.
- Names: trimmed, 1–30 characters. Chat text: trimmed, 1–1000 characters.
- History size: 20 (from settings). Allowed origins: `["http://localhost:3000"]` (from settings).
- The server sets `name` and `sent_at` on chat messages and never trusts the browser for them.
- Browser heartbeat: `ping` every 25 s; no `pong` within 10 s → close and reconnect. Reconnect waits: 1 s, 2 s, 4 s, 8 s, then 10 s each time.
- Ports: backend 8000, frontend 3000.
- One commit per task (per level). Claude drafts `learning/level-N-<name>.md` at the end of each level.

## Review Focus

Things the design implies but no feature test naturally hits. Each one has a test or a check in the task that owns the code:

1. **Sending while the socket isn't open** (connecting or reconnecting): the browser must not throw. The send button is disabled unless the status is `open` (Task 5, Task 7 manual check).
2. **One client dies mid-broadcast:** everyone else still gets the message, and the dead one is dropped (Task 3, `test_broadcast_skips_broken_connection`).
3. **Blank or whitespace-only chat text:** gets an `error`, not an empty line (Task 4, `test_blank_chat_gets_error`).
4. **Emoji and non-English text:** survives the round trip unchanged (Task 4, `test_unicode_text_round_trips`).
5. **React StrictMode mounts the hook twice in dev:** no ghost connections, and one tab counts as one person online (Task 2 and Task 5 manual check).

---

### Task 1 (Level 0): Project setup

**Files:**
- Create: `.gitignore`, `README.md`, `command.txt`, `learning/` (empty for now)
- Create: `backend/pyproject.toml` (via uv), `backend/.env.example`, `backend/app/__init__.py`, `backend/app/main.py`, `backend/app/config.py`
- Create: `backend/tests/conftest.py` (empty for now), `backend/tests/test_health.py`
- Create: `frontend/` (via `bun init --react`)

**Interfaces:**
- Produces: `app.main.app` (the FastAPI instance); `app.config.settings` with `allowed_origins: list[str]` and `history_size: int`.

- [ ] **Step 1:** In the project root run `git init`. Create `.gitignore` (Python: `.venv/`, `__pycache__/`, `.pytest_cache/`, `.env`; bun: `node_modules/`, `dist/`), a short `README.md`, and `command.txt` with a header line. Log the command.
- [ ] **Step 2:** `mkdir backend`, `cd backend`, `uv init --bare`, then `uv add "fastapi[standard]" pydantic-settings` and `uv add --dev pytest`. Expected: `pyproject.toml` and `uv.lock` exist, and `.venv/` is created.
- [ ] **Step 3:** Add to `pyproject.toml`, so tests can `import app`:
  ```toml
  [tool.pytest.ini_options]
  pythonpath = ["."]
  ```
- [ ] **Step 4: Write the failing test** `tests/test_health.py`:
  ```python
  from fastapi.testclient import TestClient
  from app.main import app

  def test_health_says_ok():
      response = TestClient(app).get("/health")
      assert response.status_code == 200
      assert response.json() == {"status": "ok"}
  ```
- [ ] **Step 5:** Run `uv run pytest -v`. Expected: FAIL (`app.main` doesn't exist yet).
- [ ] **Step 6:** Write `app/config.py`: `class Settings(BaseSettings)` with `allowed_origins: list[str] = ["http://localhost:3000"]`, `history_size: int = 20`, and `model_config = SettingsConfigDict(env_file=".env")`; then a module-level `settings = Settings()`. Write `.env.example` with both values (a list goes in as JSON: `ALLOWED_ORIGINS=["http://localhost:3000"]`).
- [ ] **Step 7:** Write `app/main.py`: `app = FastAPI(title="WebSocket Chat")`, add `CORSMiddleware` with `allow_origins=settings.allowed_origins`, and add `GET /health` returning `{"status": "ok"}`.
- [ ] **Step 8:** Run `uv run pytest -v`. Expected: 1 passed.
- [ ] **Step 9:** Run `uv run uvicorn app.main:app --reload --port 8000`, then open `http://localhost:8000/health` and `http://localhost:8000/docs`. Expected: `{"status":"ok"}` and the docs page.
- [ ] **Step 10:** From the project root: `mkdir frontend`, `cd frontend`, `bun init --react`, `bun dev`. Expected: the starter page at `http://localhost:3000`. Look at what the template made: `index.html`, `src/index.ts` (the dev server), `src/frontend.tsx`, `src/App.tsx`, and `bunfig.toml`. Check that `bunfig.toml` exposes `BUN_PUBLIC_*` env variables, which Task 5 needs.
- [ ] **Step 11: Commit** with the message `level 0: project setup`.

---

### Task 2 (Level 1): Echo

**Files:**
- Create: `backend/app/chat/__init__.py`, `backend/app/chat/router.py`, `backend/tests/test_chat_ws.py`
- Modify: `backend/app/main.py` (include the router)
- Modify: `frontend/src/App.tsx` (bare echo page)

**Interfaces:**
- Produces: `app.chat.router.router` (an `APIRouter`) with `@router.websocket("/ws") async def chat_ws(websocket: WebSocket) -> None`.

- [ ] **Step 1: Write the failing test** in `tests/test_chat_ws.py`:
  ```python
  from fastapi.testclient import TestClient
  from app.main import app

  client = TestClient(app)

  def test_echo_sends_back_text():
      with client.websocket_connect("/ws") as ws:
          ws.send_text("hello")
          assert ws.receive_text() == "hello"
  ```
- [ ] **Step 2:** `uv run pytest -v`. Expected: FAIL (no `/ws` route).
- [ ] **Step 3: Mini-steps for `chat_ws`**, running the server after each one:
  - 3a: only `await websocket.accept()`.
  - 3b: receive one text and send it back.
  - 3c: wrap it in `while True`.
  - 3d: catch `WebSocketDisconnect` and print who left. Without this, closing a tab prints an error trace.

  Then `app.include_router(router)` in `main.py`.
- [ ] **Step 4:** `uv run pytest -v`. Expected: 2 passed.
- [ ] **Step 5: Console experiment.** With the backend running, open `http://localhost:8000/health` and then DevTools → Console:
  ```js
  const ws = new WebSocket("ws://localhost:8000/ws");
  ws.onopen = () => console.log("open");
  ws.onmessage = (e) => console.log("got:", e.data);
  ws.onclose = (e) => console.log("closed", e.code);
  ws.send("hi");
  ws.close();
  ```
  Expected: `open`, `got: hi`, `closed 1005` (or 1000). In the Network tab → WS, find the `101 Switching Protocols` handshake and the Messages tab.
- [ ] **Step 6: Bare React echo page** in `App.tsx`:
  - a `useEffect` that creates the socket, sets `onmessage` to add to a `messages` state, and returns a cleanup that calls `ws.close()`;
  - a `useRef<WebSocket | null>` that holds the socket so the send button can use it;
  - an input and a Send button.
- [ ] **Step 7: Check (Review Focus 5).** With `bun dev` running, the backend log shows a connect, a disconnect, then a connect when the page loads. That's StrictMode mounting twice, and the cleanup closing the first socket. Exactly one socket stays open per tab.
- [ ] **Step 8: Commit** with the message `level 1: echo`.

---

### Task 3 (Level 2): Broadcast

**Files:**
- Create: `backend/app/chat/manager.py`, `backend/tests/test_manager.py`
- Modify: `backend/app/chat/router.py`, `backend/tests/test_chat_ws.py`

**Interfaces:**
- Produces: `class ConnectionManager` with:
  - `connections: set[WebSocket]`
  - `async def connect(self, websocket: WebSocket) -> None` (accepts and adds)
  - `def disconnect(self, websocket: WebSocket) -> None` (uses `discard`, so removing twice is safe)
  - `async def broadcast_text(self, text: str) -> None`
  - and a module-level `manager = ConnectionManager()`.

- [ ] **Step 1: Write the failing tests.** Add to `test_chat_ws.py`:
  ```python
  def test_broadcast_reaches_every_client():
      with client.websocket_connect("/ws") as a, client.websocket_connect("/ws") as b:
          a.send_text("hi")
          assert a.receive_text() == "hi"
          assert b.receive_text() == "hi"
  ```
  Create `test_manager.py` (Review Focus 2):
  ```python
  import asyncio
  from app.chat.manager import ConnectionManager

  class FakeSocket:
      def __init__(self, broken=False):
          self.broken, self.sent = broken, []
      async def send_text(self, text):
          if self.broken:
              raise RuntimeError("connection is gone")
          self.sent.append(text)

  def test_broadcast_skips_broken_connection():
      m = ConnectionManager()
      good, bad = FakeSocket(), FakeSocket(broken=True)
      m.connections.update({good, bad})
      asyncio.run(m.broadcast_text("hi"))
      assert good.sent == ["hi"]
      assert bad not in m.connections
  ```
- [ ] **Step 2:** `uv run pytest -v`. Expected: the new tests FAIL.
- [ ] **Step 3:** Write `ConnectionManager`. The one subtle part: loop over a **copy** (`list(self.connections)`), because a broken socket gets removed while you're looping. Wrap each send in `try/except Exception` and disconnect that socket on failure.
- [ ] **Step 4:** Change `chat_ws` to use `manager.connect`, `manager.broadcast_text`, and `manager.disconnect` in the `except WebSocketDisconnect`.
- [ ] **Step 5:** `uv run pytest -v`. Expected: all pass (the echo test still passes, because the sender is one of "everyone").
- [ ] **Step 6: Check.** Open two tabs at `localhost:3000`. A message sent in one shows in both.
- [ ] **Step 7: Commit** with the message `level 2: broadcast`.

---

### Task 4 (Level 3): JSON message types, validation, origin check

**Files:**
- Create: `backend/app/chat/schemas.py`
- Modify: `backend/app/chat/manager.py`, `backend/app/chat/router.py`, `backend/tests/test_chat_ws.py`, `backend/tests/conftest.py`
- Create: `frontend/src/types/messages.ts`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Produces in `schemas.py`:
  - `Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]`
  - `ChatText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]`
  - Incoming: `JoinIn(type: Literal["join"], name: Name)`, `ChatIn(type: Literal["chat"], text: ChatText)`, `PingIn(type: Literal["ping"])`
  - `ClientMessage = Annotated[JoinIn | ChatIn | PingIn, Field(discriminator="type")]` and `client_message = TypeAdapter(ClientMessage)`. Parsing is `client_message.validate_json(raw)`, which raises `ValidationError`.
  - Outgoing, each with a `type: Literal[...]` default: `ChatOut(name: str, text: str, sent_at: datetime)`, `WelcomeOut(history: list[ChatOut], online: int)`, `UserJoinedOut(name: str, online: int)`, `UserLeftOut(name: str, online: int)`, `PongOut()`, `ErrorOut(message: str)`
- Changes `ConnectionManager`: `broadcast_text` becomes `async def broadcast(self, message: BaseModel) -> None`, plus `async def send(self, websocket: WebSocket, message: BaseModel) -> None`. Both send `message.model_dump_json()`.
- In Level 3 there's no `join` yet, so chat messages go out with `name="anonymous"`. `join` is parsed but answered with `ErrorOut(message="join comes in level 4")`, which is temporary.

- [ ] **Step 1: Write the failing tests.** Replace the plain-text tests in `test_chat_ws.py` with these:
  ```python
  import pytest
  from starlette.websockets import WebSocketDisconnect

  def test_chat_is_broadcast_as_json():
      with client.websocket_connect("/ws") as a, client.websocket_connect("/ws") as b:
          a.send_json({"type": "chat", "text": "hi"})
          a.receive_json()
          got = b.receive_json()
          assert got["type"] == "chat" and got["text"] == "hi" and "sent_at" in got

  def test_invalid_json_gets_error_and_connection_stays_open():
      with client.websocket_connect("/ws") as ws:
          ws.send_text("not json")
          assert ws.receive_json()["type"] == "error"
          ws.send_json({"type": "ping"})
          assert ws.receive_json() == {"type": "pong"}

  def test_unknown_type_gets_error():
      with client.websocket_connect("/ws") as ws:
          ws.send_json({"type": "dance"})
          assert ws.receive_json()["type"] == "error"

  def test_too_long_text_gets_error():
      with client.websocket_connect("/ws") as ws:
          ws.send_json({"type": "chat", "text": "x" * 1001})
          assert ws.receive_json()["type"] == "error"

  def test_blank_chat_gets_error():
      with client.websocket_connect("/ws") as ws:
          ws.send_json({"type": "chat", "text": "   "})
          assert ws.receive_json()["type"] == "error"

  def test_unicode_text_round_trips():
      with client.websocket_connect("/ws") as ws:
          ws.send_json({"type": "chat", "text": "నమస్తే 👋"})
          assert ws.receive_json()["text"] == "నమస్తే 👋"

  def test_foreign_origin_is_refused():
      with pytest.raises(WebSocketDisconnect):
          with client.websocket_connect("/ws", headers={"origin": "http://evil.example"}):
              pass

  def test_allowed_origin_connects():
      with client.websocket_connect("/ws", headers={"origin": "http://localhost:3000"}) as ws:
          ws.send_json({"type": "ping"})
          assert ws.receive_json() == {"type": "pong"}
  ```
  Then in `conftest.py`, add an autouse fixture that clears `manager.connections` before each test, so tests don't affect each other.
- [ ] **Step 2:** `uv run pytest -v`. Expected: the new tests FAIL.
- [ ] **Step 3:** Write `schemas.py` from the Interfaces block.
- [ ] **Step 4:** Update the manager (`send`, `broadcast`). `test_manager.py` changes to broadcast a `PongOut()` and to assert `good.sent == ['{"type":"pong"}']`. `FakeSocket` keeps `send_text`.
- [ ] **Step 5:** Update `chat_ws`:
  - Origin check **before** `connect`: if an `origin` header is present and not in `settings.allowed_origins`, `await websocket.close(code=1008)` and return.
  - In the loop: `receive_text` → `client_message.validate_json` → on `ValidationError`, send `ErrorOut` and `continue`. Use `match message:` with a case per class: `ChatIn` broadcasts a `ChatOut`, with `sent_at=datetime.now(timezone.utc)`; `PingIn` sends `PongOut` to that socket only.
- [ ] **Step 6:** `uv run pytest -v`. Expected: all pass.
- [ ] **Step 7: Frontend.** Write `types/messages.ts` with one type per message, and `ServerMessage` as a union of the server ones on `type`. In `App.tsx`, send `JSON.stringify({type: "chat", text})`, and on receive `JSON.parse` and `switch (msg.type)`. Show `error` messages in red.
- [ ] **Step 8: Check.** Two tabs chat as "anonymous". In the console, `ws.send("junk")` gets an error back, and the chat still works.
- [ ] **Step 9: Commit** with the message `level 3: json protocol, validation, origin check`.

---

### Task 5 (Level 4): Join, leave, online count, real UI

**Files:**
- Modify: `backend/app/chat/manager.py`, `backend/app/chat/router.py`, `backend/tests/test_chat_ws.py`, `backend/tests/test_manager.py`
- Create: `frontend/src/config.ts`, `frontend/src/hooks/useChatSocket.ts`, `frontend/src/components/JoinForm.tsx`, `ConnectionStatus.tsx`, `OnlineCount.tsx`, `MessageList.tsx`, `MessageInput.tsx`
- Modify: `frontend/src/App.tsx` (becomes layout only)

**Interfaces:**
- `ConnectionManager` changes to:
  - `connections: dict[WebSocket, str | None]` (the name is `None` until join)
  - `async def connect(ws) -> None`
  - `def set_name(ws, name: str) -> None`
  - `def name_of(ws) -> str | None`
  - `def disconnect(ws) -> str | None` (returns the name, or `None` if they never joined)
  - `def online_count() -> int` (joined connections only)
  - `async def broadcast(message, exclude: WebSocket | None = None) -> None` (joined connections only)
  - `async def send(ws, message) -> None`
- Router rules:
  - `join` when already joined gets `ErrorOut(message="already joined")`.
  - Otherwise `set_name`, send `WelcomeOut(history=[], online=...)` to the joiner, and broadcast `UserJoinedOut` with `exclude=` the joiner.
  - `chat` before join gets `ErrorOut(message="join first")`.
  - Chat uses `name_of(ws)`.
  - On disconnect, if a name came back, broadcast `UserLeftOut`.
- Frontend:
  - `config.ts`: `export const WS_URL = process.env.BUN_PUBLIC_WS_URL ?? "ws://localhost:8000/ws";`
  - `useChatSocket(url: string)` returns `{ status: "connecting" | "open" | "closed", items: ChatItem[], online: number, joined: boolean, error: string | null, join(name: string): void, sendChat(text: string): void }`
  - `type ChatItem = { kind: "chat"; name: string; text: string; sentAt: string } | { kind: "notice"; text: string }`

- [ ] **Step 1: Write the failing tests.** Add a helper and tests to `test_chat_ws.py`, and change the Level 3 chat tests to `join` first:
  ```python
  def join(ws, name):
      ws.send_json({"type": "join", "name": name})
      return ws.receive_json()

  def test_join_gets_welcome_with_online_count():
      with client.websocket_connect("/ws") as a:
          assert join(a, "Asha") == {"type": "welcome", "history": [], "online": 1}

  def test_others_hear_about_join_and_leave():
      with client.websocket_connect("/ws") as a:
          join(a, "Asha")
          with client.websocket_connect("/ws") as b:
              join(b, "Ben")
              assert a.receive_json() == {"type": "user_joined", "name": "Ben", "online": 2}
          assert a.receive_json() == {"type": "user_left", "name": "Ben", "online": 1}

  def test_chat_before_join_gets_error():
      with client.websocket_connect("/ws") as ws:
          ws.send_json({"type": "chat", "text": "hi"})
          assert ws.receive_json() == {"type": "error", "message": "join first"}

  def test_second_join_gets_error():
      with client.websocket_connect("/ws") as ws:
          join(ws, "Asha")
          assert join(ws, "Asha again") == {"type": "error", "message": "already joined"}

  def test_blank_name_gets_error():
      with client.websocket_connect("/ws") as ws:
          assert join(ws, "   ")["type"] == "error"

  def test_server_sets_the_name_not_the_browser():
      with client.websocket_connect("/ws") as ws:
          join(ws, "Asha")
          ws.send_json({"type": "chat", "text": "hi", "name": "Hacker"})
          assert ws.receive_json()["name"] == "Asha"
  ```
  `test_manager.py`: register the fakes as joined (`m.connections.update({good: "G", bad: "B"})`).
- [ ] **Step 2:** `uv run pytest -v`. Expected: the new tests FAIL.
- [ ] **Step 3:** Update the manager and router per the Interfaces block.
- [ ] **Step 4:** `uv run pytest -v`. Expected: all pass.
- [ ] **Step 5: The hook, in mini-steps:**
  - 5a: move the socket `useEffect` and `useRef` from `App.tsx` into `useChatSocket`, returning `status`.
  - 5b: handle `welcome` (set `online`, `joined = true`), `user_joined` and `user_left` (update `online`, add a notice), `chat` (add an item), and `error` (set `error`).
  - 5c: `join` and `sendChat`, both only sending when `ws.readyState === WebSocket.OPEN`.
- [ ] **Step 6: Components.**
  - `JoinForm` (name input, shown until `joined`)
  - `ConnectionStatus` (shows `status`)
  - `OnlineCount`
  - `MessageList` (chat items and notices)
  - `MessageInput` (Send is **disabled unless `status === "open"`**, which covers Review Focus 1)

  `App.tsx` only lays them out.
- [ ] **Step 7: Check.** Three tabs: join with three names, and every tab shows 3 online. Close one: the others show "X left" and 2 online. With StrictMode, one tab still counts as one person (Review Focus 5).
- [ ] **Step 8: Commit** with the message `level 4: join, leave, online count, UI`.

---

### Task 6 (Level 5): Catch-up history

**Files:**
- Modify: `backend/app/chat/manager.py`, `backend/app/chat/router.py`, `backend/tests/test_chat_ws.py`, `backend/tests/conftest.py`
- Modify: `frontend/src/hooks/useChatSocket.ts`

**Interfaces:**
- `ConnectionManager.__init__(self, history_size: int)` adds `history: deque[ChatOut]` (`maxlen=history_size`), `def remember(self, message: ChatOut) -> None`, and `def recent(self) -> list[ChatOut]`. The module-level instance becomes `manager = ConnectionManager(settings.history_size)`. `test_manager.py` builds `ConnectionManager(history_size=5)`.
- The router calls `remember` before broadcasting a chat, and `WelcomeOut(history=manager.recent(), ...)`.
- The `conftest.py` fixture also clears `manager.history`.

- [ ] **Step 1: Write the failing tests:**
  ```python
  from app.config import settings

  def test_newcomer_gets_recent_history():
      with client.websocket_connect("/ws") as a:
          join(a, "Asha")
          for text in ["one", "two", "three"]:
              a.send_json({"type": "chat", "text": text})
              a.receive_json()
          with client.websocket_connect("/ws") as b:
              welcome = join(b, "Ben")
              assert [m["text"] for m in welcome["history"]] == ["one", "two", "three"]

  def test_history_keeps_only_the_last_n():
      n = settings.history_size
      with client.websocket_connect("/ws") as a:
          join(a, "Asha")
          for i in range(n + 5):
              a.send_json({"type": "chat", "text": f"m{i}"})
              a.receive_json()
          with client.websocket_connect("/ws") as b:
              history = join(b, "Ben")["history"]
              assert len(history) == n
              assert history[-1]["text"] == f"m{n + 4}"
  ```
- [ ] **Step 2:** `uv run pytest -v`. Expected: FAIL.
- [ ] **Step 3:** Implement per the Interfaces block. The subtle part: `deque(maxlen=...)` drops the oldest item by itself.
- [ ] **Step 4:** `uv run pytest -v`. Expected: all pass.
- [ ] **Step 5: Frontend.** On `welcome`, **replace** `items` with the history mapped to `ChatItem`s. Don't append.
- [ ] **Step 6: Check.** Chat in one tab, then open a new tab and join. The recent messages are there.
- [ ] **Step 7: Commit** with the message `level 5: catch-up history`.

---

### Task 7 (Level 6): Survive drops

**Files:**
- Modify: `frontend/src/hooks/useChatSocket.ts`, `frontend/src/components/ConnectionStatus.tsx`
- Modify: `README.md` (the run command with the ping options)

**Interfaces:**
- `status` becomes `"connecting" | "open" | "reconnecting" | "closed"`.
- Constants in the hook: `PING_INTERVAL_MS = 25_000`, `PONG_TIMEOUT_MS = 10_000`, `RETRY_DELAYS_MS = [1000, 2000, 4000, 8000, 10000]` (the last one repeats).

- [ ] **Step 1: Server-side heartbeat (explain, no new code).** Run `uv run uvicorn app.main:app --reload --port 8000 --ws-ping-interval 20 --ws-ping-timeout 20` (these are the defaults, now written out). Look at how uvicorn's ping frames drop silent clients, which then reach our `except WebSocketDisconnect` as usual. Note it in the README.
- [ ] **Step 2: Hook, in mini-steps:**
  - 2a: move socket creation into a `connect()` function inside the effect. Keep the socket, the attempt count, the timers, the saved name, and an `intentionalClose` flag in `useRef`s.
  - 2b: `onclose` (when not intentional) sets `"reconnecting"` and schedules `connect()` after `RETRY_DELAYS_MS[min(attempt, last)]`. `onopen` resets the attempt count, sets `"open"`, and re-sends `join` if a name was saved.
  - 2c: heartbeat. On open, start a `setInterval` that sends `ping` and starts a `PONG_TIMEOUT_MS` timer. `pong` clears that timer; if the timer fires, call `ws.close()`, which leads to reconnecting.
  - 2d: cleanup clears **every** timer and interval, sets `intentionalClose`, and closes the socket.
- [ ] **Step 3: `ConnectionStatus`** shows all four states. Make "reconnecting…" obvious.
- [ ] **Step 4: Checks.**
  - Stop the backend: the status shows reconnecting, Send is disabled, and the waits grow (watch the Network tab).
  - Start the backend: within 10 s the status is open, you're re-joined under the same name, and messages aren't duplicated.
  - Restart the backend while two tabs are joined: both come back. History is empty after the restart (it's in memory), and that's expected.
- [ ] **Step 5:** `uv run pytest -v`. Expected: all pass, with nothing broken on the backend.
- [ ] **Step 6: Commit** with the message `level 6: reconnect and heartbeat`.
