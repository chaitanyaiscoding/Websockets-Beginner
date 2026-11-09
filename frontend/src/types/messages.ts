// The message protocol, the same list as backend/app/chat/schemas.py.
// If you change one, change the other.

// ---------- Browser -> server ----------
export type JoinIn = { type: "join"; name: string };
export type ChatIn = { type: "chat"; text: string };
export type PingIn = { type: "ping" };

export type ClientMessage = JoinIn | ChatIn | PingIn;

// ---------- Server -> browser ----------
export type ChatOut = {
  type: "chat";
  name: string;
  text: string;
  sent_at: string; // ISO date string: JSON has no date type
};
export type WelcomeOut = { type: "welcome"; history: ChatOut[]; online: number };
export type UserJoinedOut = { type: "user_joined"; name: string; online: number };
export type UserLeftOut = { type: "user_left"; name: string; online: number };
export type PongOut = { type: "pong" };
export type ErrorOut = { type: "error"; message: string };

// A "discriminated union": TypeScript narrows on `type`, so inside
// `case "chat":` it knows the message has name, text and sent_at.
export type ServerMessage =
  | ChatOut
  | WelcomeOut
  | UserJoinedOut
  | UserLeftOut
  | PongOut
  | ErrorOut;
