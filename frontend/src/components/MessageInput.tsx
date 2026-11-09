import { useState, type FormEvent } from "react";

type Props = { onSend: (text: string) => void; disabled: boolean };

export function MessageInput({ onSend, disabled }: Props) {
  const [draft, setDraft] = useState("");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const text = draft.trim();
    if (text === "") return;
    onSend(text);
    setDraft("");
  }

  return (
    <form onSubmit={handleSubmit} className="row">
      <input
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        placeholder="Type a message"
        maxLength={1000}
        autoFocus
      />
      {/* Disabled unless connected: sending on a closed socket would throw. */}
      <button type="submit" disabled={disabled}>
        Send
      </button>
    </form>
  );
}
