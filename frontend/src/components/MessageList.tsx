import type { ChatItem } from "../hooks/useChatSocket";

export function MessageList({ items }: { items: ChatItem[] }) {
  if (items.length === 0) return <p className="empty">No messages yet. Say hi!</p>;

  return (
    <ul className="messages">
      {items.map((item, i) =>
        // Index keys are OK: the list only grows at the end, or is replaced whole on welcome.
        item.kind === "chat" ? (
          <li key={i}>
            <strong>{item.name}</strong>: {item.text}{" "}
            <small>{new Date(item.sentAt).toLocaleTimeString()}</small>
          </li>
        ) : (
          <li key={i} className="notice">
            {item.text}
          </li>
        ),
      )}
    </ul>
  );
}
