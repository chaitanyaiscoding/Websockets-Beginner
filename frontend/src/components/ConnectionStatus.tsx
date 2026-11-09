import type { Status } from "../hooks/useChatSocket";

const LABELS: Record<Status, string> = {
  connecting: "🟡 Connecting…",
  open: "🟢 Connected",
  reconnecting: "🟠 Connection lost. Reconnecting…",
  closed: "🔴 Disconnected",
};

export function ConnectionStatus({ status }: { status: Status }) {
  return <p className={`status status-${status}`}>{LABELS[status]}</p>;
}
