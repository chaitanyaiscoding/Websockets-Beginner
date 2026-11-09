import { useState, type FormEvent } from "react";

type Props = { onJoin: (name: string) => void; disabled: boolean };

export function JoinForm({ onJoin, disabled }: Props) {
  const [name, setName] = useState("");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = name.trim();
    if (trimmed !== "") onJoin(trimmed);
  }

  return (
    <form onSubmit={handleSubmit} className="row">
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Your name"
        maxLength={30}
        autoFocus
      />
      <button type="submit" disabled={disabled}>
        Join
      </button>
    </form>
  );
}
