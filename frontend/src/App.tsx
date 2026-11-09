import { useEffect, useRef, useState, type FormEvent } from "react";
import "./index.css";
import type { ChatOut, ClientMessage, ServerMessage } from "./types/messages";

// Level 3: messages are JSON with a "type" field.
// Later (Task 5) the socket code moves into a hook, useChatSocket, and the URL into config.ts.
const WS_URL = "ws://localhost:8000/ws";

type Status = "connecting" | "open" | "closed";

export function App() {
  // The socket lives in a ref, not in state: changing it should not re-render,
  // and the send handler needs to reach the same socket the effect created.
  const socketRef = useRef<WebSocket | null>(null);

  const [status, setStatus] = useState<Status>("connecting");
  const [messages, setMessages] = useState<ChatOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState("");

  useEffect(() => {
    const ws = new WebSocket(WS_URL);
    socketRef.current = ws;

    ws.onopen = () => setStatus("open");

    ws.onmessage = (event: MessageEvent<string>) => {
      // The wire carries text. Parse it, then switch on "type".
      // `as ServerMessage` trusts the server; the server validates its own output with Pydantic.
      const msg = JSON.parse(event.data) as ServerMessage;
      switch (msg.type) {
        case "chat":
          setMessages((prev) => [...prev, msg]);
          setError(null);
          break;
        case "error":
          setError(msg.message);
          break;
        case "pong":
          // Nothing to show yet. Level 6 uses pong for the heartbeat.
          break;
        default:
          // welcome, user_joined and user_left arrive in Level 4.
          break;
      }
    };

    ws.onerror = () => console.warn("WebSocket error (a close event follows)");
    ws.onclose = () => setStatus("closed");

    // Cleanup: runs on unmount, and once extra in dev because of StrictMode.
    // Detach the handlers first, so this old socket's late "close" event
    // can't overwrite the status of the new socket from the second mount.
    return () => {
      ws.onopen = null;
      ws.onmessage = null;
      ws.onerror = null;
      ws.onclose = null;
      ws.close();
      if (socketRef.current === ws) socketRef.current = null;
    };
  }, []);

  // One place that turns a typed message into JSON and sends it.
  // send() throws if the socket isn't open yet, so check readyState first.
  function send(message: ClientMessage) {
    const ws = socketRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify(message));
  }

  function handleSend(event: FormEvent) {
    event.preventDefault();
    const text = draft.trim();
    if (text === "") return;
    send({ type: "chat", text });
    setDraft("");
  }

  return (
    <div className="app">
      <h1>WebSocket Chat</h1>
      <p>
        Status: <strong>{status}</strong>
      </p>

      <form onSubmit={handleSend}>
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Type a message"
          maxLength={1000}
          autoFocus
        />
        <button type="submit" disabled={status !== "open"}>
          Send
        </button>
      </form>

      {error && <p style={{ color: "crimson" }}>Error: {error}</p>}

      <ul>
        {messages.map((m, i) => (
          // Index keys are fine here: the list only ever grows at the end.
          <li key={i}>
            <strong>{m.name}</strong>: {m.text}{" "}
            <small>{new Date(m.sent_at).toLocaleTimeString()}</small>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default App;
