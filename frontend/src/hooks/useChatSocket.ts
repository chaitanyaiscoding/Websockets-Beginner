import { useCallback, useEffect, useRef, useState } from "react";
import type { ChatOut, ClientMessage, ServerMessage } from "../types/messages";

// ALL WebSocket code lives in this hook. Components never touch the socket:
// they get state (items, online, status...) and two functions (join, sendChat).
// This is the part of the template that carries over to the team board.

export type Status = "connecting" | "open" | "reconnecting" | "closed";

// What the message list shows: chat lines, plus notices like "Ben joined".
export type ChatItem =
  | { kind: "chat"; name: string; text: string; sentAt: string }
  | { kind: "notice"; text: string };

// ---------- Level 6: heartbeat and reconnect settings ----------

// Every 25 s we ask the server "are you still there?" ...
const PING_INTERVAL_MS = 25_000;
// ... and if no pong comes back within 10 s, we treat the connection as dead.
const PONG_TIMEOUT_MS = 10_000;
// Waits between reconnect attempts. They grow, so a server that's down isn't
// hammered by every open tab at once. The last one repeats forever.
const RETRY_DELAYS_MS = [1000, 2000, 4000, 8000, 10000];

function toChatItem(m: ChatOut): ChatItem {
  return { kind: "chat", name: m.name, text: m.text, sentAt: m.sent_at };
}

export function useChatSocket(url: string) {
  // The current socket, so join/sendChat (outside the effect) can reach it.
  const socketRef = useRef<WebSocket | null>(null);
  // The name we joined with. Kept in a ref so a reconnect can re-join by itself.
  // A ref, not state: the effect's handlers need the latest value without re-running.
  const nameRef = useRef<string | null>(null);
  // The name in a join we sent but the server hasn't confirmed (with welcome) yet.
  const pendingNameRef = useRef<string | null>(null);

  const [status, setStatus] = useState<Status>("connecting");
  const [items, setItems] = useState<ChatItem[]>([]);
  const [online, setOnline] = useState(0);
  const [joined, setJoined] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // These live in the effect's closure, not in refs: each run of the effect
    // (StrictMode runs it twice in dev) gets its OWN copies, so the first run's
    // timers can never touch the second run's socket.
    let ws: WebSocket | null = null;
    let attempt = 0;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;
    let pingTimer: ReturnType<typeof setInterval> | undefined;
    let pongTimer: ReturnType<typeof setTimeout> | undefined;
    let stopped = false; // true once cleanup ran: an intentional close, don't reconnect

    function stopHeartbeat() {
      clearInterval(pingTimer);
      clearTimeout(pongTimer);
    }

    function startHeartbeat(socket: WebSocket) {
      pingTimer = setInterval(() => {
        socket.send(JSON.stringify({ type: "ping" } satisfies ClientMessage));
        // Start the countdown. A pong clears it; if it fires, the connection is dead.
        clearTimeout(pongTimer);
        pongTimer = setTimeout(() => {
          console.warn("No pong in time: treating the connection as dead");
          handleDrop(socket);
        }, PONG_TIMEOUT_MS);
      }, PING_INTERVAL_MS);
    }

    // Called when a socket dies, whether from a close event or a missed pong.
    function handleDrop(socket: WebSocket) {
      // Only react once, and only for the current socket.
      // (A missed pong and a late close event can both arrive for the same socket.)
      if (socket !== ws) return;
      ws = null;
      socketRef.current = null;
      stopHeartbeat();

      // Detach and close. After a missed pong the socket may still look "open",
      // and a dead network can take a long time to deliver the close event.
      // We don't wait for it.
      socket.onopen = socket.onmessage = socket.onerror = socket.onclose = null;
      socket.close();

      if (stopped) return;
      setStatus("reconnecting");
      // If we never joined, there's nothing to restore: show the join form again.
      if (nameRef.current === null) setJoined(false);

      const delay = RETRY_DELAYS_MS[Math.min(attempt, RETRY_DELAYS_MS.length - 1)];
      attempt += 1;
      retryTimer = setTimeout(connect, delay);
    }

    function connect() {
      const socket = new WebSocket(url);
      ws = socket;
      socketRef.current = socket;

      socket.onopen = () => {
        attempt = 0; // a successful connection resets the growing waits
        setStatus("open");
        startHeartbeat(socket);
        // Reconnected after a drop: the server forgot us, so join again under the
        // same name. Its welcome then gives us the current history and online count.
        if (nameRef.current !== null) {
          pendingNameRef.current = nameRef.current;
          socket.send(JSON.stringify({ type: "join", name: nameRef.current } satisfies ClientMessage));
        }
      };

      socket.onmessage = (event: MessageEvent<string>) => {
        const msg = JSON.parse(event.data) as ServerMessage;
        switch (msg.type) {
          case "welcome":
            // REPLACE, don't append: welcome is the full current state.
            // After a reconnect, appending would show every message twice.
            nameRef.current = pendingNameRef.current;
            setItems(msg.history.map(toChatItem));
            setOnline(msg.online);
            setJoined(true);
            setError(null);
            break;
          case "user_joined":
            setOnline(msg.online);
            setItems((prev) => [...prev, { kind: "notice", text: `${msg.name} joined` }]);
            break;
          case "user_left":
            setOnline(msg.online);
            setItems((prev) => [...prev, { kind: "notice", text: `${msg.name} left` }]);
            break;
          case "chat":
            // Updater form: several messages can arrive before React re-renders.
            setItems((prev) => [...prev, toChatItem(msg)]);
            break;
          case "error":
            setError(msg.message);
            break;
          case "pong":
            // The server answered: the connection is alive. Stop the countdown.
            clearTimeout(pongTimer);
            break;
        }
      };

      socket.onerror = () => console.warn("WebSocket error (a close event follows)");
      socket.onclose = () => handleDrop(socket);
    }

    connect();

    // Cleanup: runs on unmount, and once extra in dev because of StrictMode.
    // Stop EVERY timer, and mark the close as intentional so nothing reconnects.
    return () => {
      stopped = true;
      clearTimeout(retryTimer);
      stopHeartbeat();
      if (ws) {
        const socket = ws;
        ws = null;
        socket.onopen = socket.onmessage = socket.onerror = socket.onclose = null;
        socket.close();
      }
      socketRef.current = null;
    };
  }, [url]);

  // One place that turns a typed message into JSON and sends it.
  // send() throws if the socket isn't open, so check readyState first.
  const send = useCallback((message: ClientMessage) => {
    const ws = socketRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    setError(null);
    ws.send(JSON.stringify(message));
  }, []);

  const join = useCallback(
    (name: string) => {
      pendingNameRef.current = name;
      send({ type: "join", name });
    },
    [send],
  );
  const sendChat = useCallback((text: string) => send({ type: "chat", text }), [send]);

  return { status, items, online, joined, error, join, sendChat };
}
