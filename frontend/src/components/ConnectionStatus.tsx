import type { Status } from "../hooks/useChatSocket";

const LABELS: Record<Status, string> = {
  connecting: "🟡 Connecting…",
  open: "🟢 Connected",
  closed: "🔴 Disconnected (reload the page)",
};

export function ConnectionStatus({ status }: { status: Status }) {
  return <p className="status">{LABELS[status]}</p>;
}
