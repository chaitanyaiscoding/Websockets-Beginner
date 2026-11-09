import { useCallback, useEffect, useRef, useState } from "react";
import type { ChatOut, ClientMessage, ServerMessage } from "../types/messages";

// ALL WebSocket code lives in this hook. Components never touch the socket:
// they get state (items, online, status...) and two functions (join, sendChat).
// This is the part of the template that carries over to the team board.

export type Status = "connecting" | "open" | "closed";

// What the message list shows: chat lines, plus notices like "Ben joined".
export type ChatItem =
  | { kind: "chat"; name: string; text: string; sentAt: string }
  | { kind: "notice"; text: string };

function toChatItem(m: ChatOut): ChatItem {
  return { kind: "chat", name: m.name, text: m.text, sentAt: m.sent_at };
}

export function useChatSocket(url: string) {
  // The socket lives in a ref: changing it must not re-render, and
  // join/sendChat need the same socket the effect created.
  const socketRef = useRef<WebSocket | null>(null);

  const [status, setStatus] = useState<Status>("connecting");
  const [items, setItems] = useState<ChatItem[]>([]);
  const [online, setOnline] = useState(0);
  const [joined, setJoined] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const ws = new WebSocket(url);
    socketRef.current = ws;

    ws.onopen = () => setStatus("open");

    ws.onmessage = (event: MessageEvent<string>) => {
      const msg = JSON.parse(event.data) as ServerMessage;
      switch (msg.type) {
        case "welcome":
          // REPLACE, don't append: welcome is the full current state.
          // (In Level 6 this also arrives after a reconnect. Appending would duplicate.)
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
          // Level 6 uses pong for the heartbeat.
          break;
      }
    };

    ws.onerror = () => console.warn("WebSocket error (a close event follows)");
    ws.onclose = () => {
      setStatus("closed");
      // The server forgets us when the connection closes, so we're no longer joined.
      setJoined(false);
    };

    // Cleanup: runs on unmount, and once extra in dev because of StrictMode.
    // Detach the handlers first, so this old socket's late "close" event
    // can't overwrite the state of the new socket from the second mount.
    return () => {
      ws.onopen = null;
      ws.onmessage = null;
      ws.onerror = null;
      ws.onclose = null;
      ws.close();
      if (socketRef.current === ws) socketRef.current = null;
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

  const join = useCallback((name: string) => send({ type: "join", name }), [send]);
  const sendChat = useCallback((text: string) => send({ type: "chat", text }), [send]);

  return { status, items, online, joined, error, join, sendChat };
}
