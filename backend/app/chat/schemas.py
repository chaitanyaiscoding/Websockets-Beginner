"""The message protocol: every message that can travel over /ws.

Every message is JSON with a "type" field. The frontend has the same list
in src/types/messages.ts. If you change one, change the other.
"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, TypeAdapter

# Reusable string rules. strip_whitespace runs first, so "   " becomes ""
# and then fails min_length=1. That's how blank messages get rejected.
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]
ChatText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


# ---------- Browser -> server ----------
# "type" has NO default here: the browser must say what kind of message it is.

class JoinIn(BaseModel):
    type: Literal["join"]
    name: Name


class ChatIn(BaseModel):
    type: Literal["chat"]
    text: ChatText


class PingIn(BaseModel):
    type: Literal["ping"]


# A "discriminated union": Pydantic reads "type" first, then validates
# against exactly the one matching class. Unknown types fail cleanly.
ClientMessage = Annotated[JoinIn | ChatIn | PingIn, Field(discriminator="type")]

# A TypeAdapter lets us validate a raw JSON string straight into one of the classes:
#   client_message.validate_json('{"type": "ping"}')  ->  PingIn(type="ping")
# It raises pydantic.ValidationError for bad JSON, unknown types, or bad fields.
client_message = TypeAdapter(ClientMessage)


# ---------- Server -> browser ----------
# "type" HAS a default: the server always knows what it's sending,
# so we write ChatOut(name=..., text=..., sent_at=...) without repeating it.

class ChatOut(BaseModel):
    type: Literal["chat"] = "chat"
    name: str
    text: str
    sent_at: datetime


class WelcomeOut(BaseModel):
    type: Literal["welcome"] = "welcome"
    history: list[ChatOut]
    online: int


class UserJoinedOut(BaseModel):
    type: Literal["user_joined"] = "user_joined"
    name: str
    online: int


class UserLeftOut(BaseModel):
    type: Literal["user_left"] = "user_left"
    name: str
    online: int


class PongOut(BaseModel):
    type: Literal["pong"] = "pong"


class ErrorOut(BaseModel):
    type: Literal["error"] = "error"
    message: str
