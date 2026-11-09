import { useEffect, useRef, useState, type FormEvent } from "react";
import "./index.css";

// Level 1: a bare echo page.
// Later (Task 5) this moves into a hook, useChatSocket, and the URL into config.ts.
const WS_URL = "ws://localhost:8000/ws";

type Status = "connecting" | "open" | "closed";

export function App() {
  // The socket lives in a ref, not in state: changing it should not re-render,
  // and the send handler needs to reach the same socket the effect created.
  const socketRef = useRef<WebSocket | null>(null);

  const [status, setStatus] = useState<Status>("connecting");
  const [messages, setMessages] = useState<string[]>([]);
  const [draft, setDraft] = useState("");

  useEffect(() => {
    // 1. Open the connection once, when the page mounts.
    const ws = new WebSocket(WS_URL);
    socketRef.current = ws;

    // 2. React to the four socket events.
    ws.onopen = () => setStatus("open");
    ws.onmessage = (event: MessageEvent<string>) => {
      // Use the updater form: several messages can arrive before React re-renders.
      setMessages((prev) => [...prev, event.data]);
    };
    ws.onerror = () => console.warn("WebSocket error (a close event follows)");
    ws.onclose = () => setStatus("closed");

    // 3. Cleanup: runs on unmount, and once extra in dev because of StrictMode.
    //    Detach the handlers first, so this old socket's late "close" event
    //    can't overwrite the status of the new socket from the second mount.
    return () => {
      ws.onopen = null;
      ws.onmessage = null;
      ws.onerror = null;
      ws.onclose = null;
      ws.close();
      if (socketRef.current === ws) socketRef.current = null;
    };
  }, []); // [] = connect once, not on every render

  function handleSend(event: FormEvent) {
    event.preventDefault();
    const ws = socketRef.current;
    const text = draft.trim();
    // send() throws if the socket isn't open yet, so check readyState first.
    if (!ws || ws.readyState !== WebSocket.OPEN || text === "") return;
    ws.send(text);
    setDraft("");
  }

  return (
    <div className="app">
      <h1>WebSocket Echo</h1>
      <p>
        Status: <strong>{status}</strong>
      </p>

      <form onSubmit={handleSend}>
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Type a message"
          autoFocus
        />
        <button type="submit" disabled={status !== "open"}>
          Send
        </button>
      </form>

      <ul>
        {messages.map((message, i) => (
          // Index keys are fine here: the list only ever grows at the end.
          <li key={i}>{message}</li>
        ))}
      </ul>
    </div>
  );
}

export default App;
