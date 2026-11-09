import "./index.css";
import { ConnectionStatus } from "./components/ConnectionStatus";
import { JoinForm } from "./components/JoinForm";
import { MessageInput } from "./components/MessageInput";
import { MessageList } from "./components/MessageList";
import { OnlineCount } from "./components/OnlineCount";
import { WS_URL } from "./config";
import { useChatSocket } from "./hooks/useChatSocket";

// Level 4: App is layout only. All socket logic is in useChatSocket.
export function App() {
  const { status, items, online, joined, error, join, sendChat } = useChatSocket(WS_URL);
  const isOpen = status === "open";

  return (
    <div className="app chat">
      <h1>WebSocket Chat</h1>
      <ConnectionStatus status={status} />

      {joined ? (
        <>
          <OnlineCount online={online} />
          <MessageList items={items} />
          <MessageInput onSend={sendChat} disabled={!isOpen} />
        </>
      ) : (
        <JoinForm onJoin={join} disabled={!isOpen} />
      )}

      {error && <p className="error">Error: {error}</p>}
    </div>
  );
}

export default App;
