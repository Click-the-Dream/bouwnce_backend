# BOUNWCE Realtime (WebSocket) Contract

**Audience:** Frontend / mobile clients.

**Status:** Current as of the group-chat release.

Server-side source of truth:

| Area                             | File                                   |
| -------------------------------- | -------------------------------------- |
| Direct-message (DM) entry point  | `app/service/mobile_events_service.py` |
| DM delivery / dedup / typing     | `app/service/ws_chat.py`               |
| DM presence / fan-out / catch-up | `app/service/ws_presence.py`           |
| DM frame schemas                 | `app/matching_ground/schema/chat.py`   |
| Group entry point                | `app/service/group_ws_service.py`      |
| DM route                         | `app/api/v1/mobile_events.py`          |
| Group route                      | `app/api/v1/group_ws.py`               |

All frames are **JSON objects**. Every server frame has a string `type`; almost all
carry a `data` object. Some frames add a top-level field (`client_id`, `sender`).

---

## 1. Endpoints

Both sockets authenticate with the **access token passed as a query parameter**
(browsers cannot set an `Authorization` header on a WebSocket handshake).

| Chat                  | URL                                  | Required query params |
| --------------------- | ------------------------------------ | --------------------- |
| Direct messages (1:1) | `wss://<host>/api/v1/events/ws`      | `token`               |
| Group chat            | `wss://<host>/api/v1/groups/ws/chat` | `token`, `group_id`   |

- `token` — the same JWT access token used for REST (`Authorization: Bearer …`).
  It must be of type `access`.
- `group_id` — the group's UUID. Non-UUID values are rejected by request
  validation before the handler runs.

> **Token lifetime:** the token is verified **only at connect time**. Get a fresh
> access token for every new socket. An expired token fails the handshake (see
> §2.3); it does not drop an already-open socket.

Example:

```js
const ws = new WebSocket(
  `wss://api.example.com/api/v1/groups/ws/chat?token=${accessToken}&group_id=${groupId}`,
);
```

---

## 2. Connection lifecycle

### 2.1 Open

1. Client opens the socket with the query params above.
2. Server validates the token (and, for groups, that the user is an **active member**).
3. Server `accept()`s the socket.
4. Server registers the connection and performs a one-time catch-up (§7).
5. Server sends a **ready** frame:
   - DM → `chat.ready`
   - Group → `group.ready`
6. Server enters the receive loop.

Treat the **ready frame as the signal that the connection is live and the initial
catch-up has been sent**. Frames that arrive before it (presence snapshot,
`bouwnce.system`) are best-effort ordering.

### 2.2 Heartbeat

Clients should send a ping on an idle interval and watch for the pong:

```json
{ "type": "ping" }
```

```json
{ "type": "pong" }
```

Presence/online status is backed by a Redis key with a **75 second TTL** refreshed
every ~37 s. After an abrupt disconnect a user is reported offline within ~75 s.

### 2.3 Rejection / close codes

Rejections happen **before** `accept()`. With an ASGI server (uvicorn) this is
returned as a **rejected HTTP upgrade (403)** and the browser sees `onclose` with
code `1006` — you generally **cannot read a `1008` close code client-side**.

| Close code          | Where | Cause                                                                                                                     |
| ------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------- |
| `1008` (pre-accept) | DM    | Missing `token`; token not of type `access`; token missing `sub`.                                                         |
| `1008` (pre-accept) | Group | Invalid/expired token and missing `token`; missing `group_id`; user is **not an active member**; membership lookup error. |
| `1000`              | Both  | Normal closure (either side).                                                                                             |
| `1006`              | Both  | Abnormal closure (network drop), or the server-side rejection above surfaced to the browser.                              |

**Client rule of thumb:** if the socket fails to open, re-authenticate (refresh the
access token). For group sockets, also re-check membership over REST before retrying.

---

## 3. Shared objects

### 3.1 `UserLite` (DM frames)

```jsonc
{
  "id": "3f1c…", // uuid string
  "username": "jane", // string | null
  "full_name": "Jane Doe", // string | null
  "profile_pic": { "url": "https://…" }, // object | null
}
```

### 3.2 `User` (group `sender` field)

Group message frames carry a top-level `sender` that is the **full serialized user
record** (`User.to_dict()`), not the trimmed `UserLite`. Fields you can rely on:
`id`, `email`, `full_name`, `username`, `bio`, `profile_pic`, `role`, `gender`,
`created_at`, `updated_at`, `is_store_owner`, … (all user columns except the
deletion flags). Prefer `full_name || username` for display.

### 3.3 `GroupMessage` (group `data`)

```jsonc
{
  "id": "uuid",
  "group_id": "uuid",
  "sender_id": "uuid",
  "body": "hello team",
  "created_at": "2026-10-11T12:00:00+00:00", // ISO-8601
  "updated_at": "2026-10-11T12:00:00+00:00",
  "edited_at": null, // ISO-8601 | null
  "is_edited": false,
  "media_type": null, // "image" | "video" | "file" | "audio" | null
  "media_urls": null, // string[] | null
  "media_names": null, // string[] | null
  "reply_to_message_id": null, // uuid | null
  "mentioned_user_ids": null, // uuid string[] | null
  "read_count": 0,
}
```

### 3.4 `ChatMessageData` (DM `data`)

```jsonc
{
  "id": "uuid",
  "conversation_id": "uuid",
  "sender_id": "uuid",
  "recipient_id": "uuid",
  "body": "hi", // string | null
  "read_at": null, // ISO-8601 | null
  "media_type": null, // "image" | "video" | "file" | null
  "media_urls": null, // string[] | null
  "media_name": null, // string | null
  "reply_to_message_id": null, // uuid | null
  "created_at": "2026-10-11T12:00:00+00:00",
  "updated_at": "2026-10-11T12:00:00+00:00",
  "sender": {/* UserLite */},
  "recipient": {/* UserLite */},
  "reply_to_message": false, // false, or a ChatMessageReplyData object
}
```

---

## 4. Direct messages — `/api/v1/events/ws`

### 4.1 Client → Server

| `type`              | Purpose                                     | Required fields                                   |
| ------------------- | ------------------------------------------- | ------------------------------------------------- |
| `ping`              | Liveness                                    | —                                                 |
| `chat.send`         | Send a text message                         | `recipient_id`, `body`                            |
| `chat.upload_media` | Send media (already uploaded to Cloudinary) | `recipient_id`, `media_urls`, `media_type`        |
| `chat.read`         | Mark conversation / message read            | `recipient_id` (+ `message_id` unless `mark_all`) |
| `chat.typing`       | Typing indicator                            | `user_id` (the _other_ user), `is_typing`         |

`type` is matched case-insensitively after trimming.

#### `chat.send`

```json
{
  "type": "chat.send",
  "recipient_id": "9b2…",
  "body": "hello!",
  "client_id": "local-42",
  "reply_to_message_id": null
}
```

| Field                 | Type                | Notes                           |
| --------------------- | ------------------- | ------------------------------- |
| `recipient_id`        | uuid                | other user                      |
| `body`                | string              | 1–4000 chars                    |
| `client_id`           | string ≤ 64 \| null | your optimistic id; echoed back |
| `reply_to_message_id` | uuid \| null        | message being replied to        |

#### `chat.upload_media`

```json
{
  "type": "chat.upload_media",
  "recipient_id": "9b2…",
  "client_id": "local-43",
  "media_urls": ["https://res.cloudinary.com/<cloud>/image/upload/v1/abc.jpg"],
  "media_type": "image",
  "file_name": "photo.jpg",
  "body": "look at this",
  "reply_to_message_id": null
}
```

| Field        | Type                 | Notes                                                                    |
| ------------ | -------------------- | ------------------------------------------------------------------------ |
| `media_type` | string               | `image` \| `video` \| `file` (rejected otherwise)                        |
| `media_urls` | string[]             | **must** be `https://res.cloudinary.com/<CLOUDINARY_NAME>/…` secure URLs |
| `file_name`  | string ≤ 255 \| null | original file name                                                       |
| `body`       | string \| null       | optional caption, ≤ 4000 chars                                           |

Get a signed upload target first via `POST /api/v1/uploads/chat/sign`
(`{"upload_type":"image|video|file","count":1,"file_name":"…"}`), upload to
Cloudinary, then send the returned secure URL here.

#### `chat.read`

```json
{ "type": "chat.read", "recipient_id": "9b2…", "mark_all": true }
```

```json
{
  "type": "chat.read",
  "recipient_id": "9b2…",
  "mark_all": false,
  "message_id": "aa1…"
}
```

| Field          | Type         | Notes                                                      |
| -------------- | ------------ | ---------------------------------------------------------- |
| `recipient_id` | uuid         | the other participant                                      |
| `mark_all`     | bool         | default `true`; when `false`, `message_id` is **required** |
| `message_id`   | uuid \| null | last read message                                          |

#### `chat.typing`

```json
{ "type": "chat.typing", "user_id": "9b2…", "is_typing": true }
```

`user_id` is the **other** participant. The frame is fanned out to **both**
participants; ignore events whose `data.user.id` is your own id.

### 4.2 Server → Client

| `type`                 | When                                                        | `data`                                                                            |
| ---------------------- | ----------------------------------------------------------- | --------------------------------------------------------------------------------- |
| `chat.ready`           | once after connect                                          | `{ "user_id": uuid }`                                                             |
| `pong`                 | reply to `ping`                                             | —                                                                                 |
| `bouwnce.system`       | once after connect                                          | `{ "user": { id, email, username, full_name, profile_pic } }`                     |
| `user.online.snapshot` | once after connect                                          | `{ "items": [ { "user": UserLite, "online": bool } ] }`                           |
| `user.online`          | partner connects/disconnects (and for you)                  | `{ "user": UserLite, "online": bool }`                                            |
| `chat.send.ack`        | immediately after a valid `chat.send` / `chat.upload_media` | `{ sender_id, recipient_id, client_id }`                                          |
| `chat.sent`            | after your message is persisted                             | `{ "conversation_id": uuid, "message": ChatMessageData }` (top-level `client_id`) |
| `chat.message`         | incoming message from the other user                        | `ChatMessageData`                                                                 |
| `chat.read.ack`        | reply to your `chat.read`                                   | `{ conversation_id, reader_id, read, updated }`                                   |
| `chat.read.updated`    | when either side marks messages read                        | `{ conversation_id, message_id, reader_id, read, updated }`                       |
| `chat.typing`          | other user's typing state                                   | `{ conversation_id, user: UserLite, is_typing }`                                  |
| `error`                | validation / handler failure                                | `{ error, message }` (see §8)                                                     |

Notes:

- `chat.send.ack` is optimistic — it is sent **before** the DB write. Use it to
  mark the bubble "sending" and match it to your local `client_id`.
- `chat.sent` is the server-confirmed copy of **your own** message and echoes your
  `client_id` at the top level. Render from this.
- `chat.message` is how you receive **other users'** messages.
- `chat.read.updated` is published to **both** participants (including the reader),
  so apply it idempotently using `updated`.

### 4.3 Example DM session

```text
client → { "type": "ping" }
server → { "type": "pong" }

server → { "type": "bouwnce.system", "data": { "user": { "id": "…", "username": "bouwnce", … } } }
server → { "type": "user.online.snapshot", "data": { "items": [ … ] } }
server → { "type": "chat.ready", "data": { "user_id": "…" } }

client → { "type": "chat.send", "recipient_id": "9b2…", "body": "hey", "client_id": "c1" }
server → { "type": "chat.send.ack", "data": { "sender_id": "…", "recipient_id": "9b2…", "client_id": "c1" } }
server → { "type": "chat.sent", "client_id": "c1", "data": { "conversation_id": "…", "message": { … } } }

client → { "type": "chat.typing", "user_id": "9b2…", "is_typing": true }
server → (to 9b2…) { "type": "chat.typing", "data": { "conversation_id": "…", "user": { … }, "is_typing": true } }

# other user replies
server → { "type": "chat.message", "data": { "id": "…", "sender_id": "9b2…", "recipient_id": "…", "body": "hi", … } }
```

---

## 5. Group chat — `/api/v1/groups/ws/chat`

Only **active members** of the group can open the socket. A non-member (or bad
token / missing `group_id`) is rejected before accept.

### 5.1 Client → Server

| `type`          | Aliases         | Purpose                     |
| --------------- | --------------- | --------------------------- |
| `ping`          | —               | Liveness (`pong` reply)     |
| `group_message` | `group.message` | Send a message to the group |
| `group_typing`  | `group.typing`  | Typing indicator            |

`type` is matched case-insensitively after trimming. Any other value yields an
`error` frame (§8).

#### `group_message` / `group.message`

```json
{
  "type": "group_message",
  "body": "standup in 5",
  "client_id": "local-7",
  "media_type": "image",
  "media_urls": ["https://res.cloudinary.com/<cloud>/image/upload/v1/abc.jpg"],
  "media_names": ["photo.jpg"],
  "reply_to_message_id": "aa1…",
  "mentioned_user_ids": ["9b2…", "7c4…"]
}
```

| Field                 | Type             | Notes                                                                                                                              |
| --------------------- | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `body`                | string           | **required, non-empty**. The WS path enforces non-empty only; keep to ≤4000 chars for parity with the REST endpoint and DB sizing. |
| `client_id`           | string \| null   | echoed on the ack                                                                                                                  |
| `media_type`          | string \| null   | `image` \| `video` \| `file` \| `audio`                                                                                            |
| `media_urls`          | string[] \| null | media URLs                                                                                                                         |
| `media_names`         | string[] \| null | original file names                                                                                                                |
| `reply_to_message_id` | uuid \| null     | message being replied to                                                                                                           |
| `mentioned_user_ids`  | uuid[] \| null   | every id must be an active member                                                                                                  |

An empty body returns an `error` frame and sends nothing.

#### `group_typing` / `group.typing`

```json
{ "type": "group_typing", "is_typing": true }
```

Broadcast to **all other members only** — the sender never receives its own
typing event.

### 5.2 Server → Client

| `type`               | When                                                    | Payload                                                                                        |
| -------------------- | ------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `group.ready`        | once after connect & catch-up                           | `{ "type": "group.ready", "data": { "group_id": uuid, "user_id": uuid } }`                     |
| `pong`               | reply to `ping`                                         | `{ "type": "pong" }`                                                                           |
| `group_message`      | a message is broadcast in the group                     | `{ "type": "group_message", "data": GroupMessage, "sender": User }`                            |
| `group_message_sent` | ack for **your** `group_message`                        | `{ "type": "group_message_sent", "client_id": "…", "data": GroupMessage }`                     |
| `group_typing`       | another member is typing                                | `{ "type": "group_typing", "data": { "group_id": uuid, "user_id": uuid, "is_typing": bool } }` |
| `error`              | invalid JSON / unknown type / empty body / send failure | `{ "type": "error", "message": "…" }`                                                          |

Notes:

- The sender receives **both**: the broadcast `group_message` and the
  `group_message_sent` ack (which carries your `client_id`). Match the ack to your
  optimistic bubble via `client_id`, and dedupe the broadcast by `data.id`.
- `group_message.data` is the persisted `GroupMessage`; the top-level `sender` is
  the full user record (§3.2).
- Typing events are **not persisted** and are not replayed after a reconnect.

### 5.3 Example group session

```text
server → { "type": "group.ready", "data": { "group_id": "g1", "user_id": "u1" } }

client → { "type": "group_message", "body": "hi all", "client_id": "c1" }
server → { "type": "group_message_sent", "client_id": "c1", "data": { "id": "m1", "body": "hi all", … } }
# every member (including the sender) also gets the broadcast:
server → { "type": "group_message", "data": { "id": "m1", "sender_id": "u1", "body": "hi all", … }, "sender": { … } }

client → { "type": "group_typing", "is_typing": true }
server → (to other members) { "type": "group_typing", "data": { "group_id": "g1", "user_id": "u1", "is_typing": true } }
```

---

## 6. Delivery, ordering & deduplication

- **Idempotency key:** every message frame carries a stable `data.id`. Treat it as
  the unique message id and ignore duplicates.
- **At-least-once, not exactly-once:** a message can reach a client on more than
  one path (direct socket delivery, Redis pub/sub across workers, reconnect
  catch-up, multi-device). **Always dedupe by `data.id`** before rendering.
- **Multi-device:** every socket a user has open receives messages. A DM you send
  is fanned out to the sender's other sockets too; dedupe there as well.
- **Ordering:** messages within a replay stream are ordered; there is no global
  cross-path ordering guarantee. Prefer `created_at` / stream order for display
  and `data.id` for identity.
- **Typing:** never persisted, best-effort, sender-excluded in groups.

## 7. Reconnect & catch-up

Both sockets replay missed messages on (re)connect from a per-user/per-group Redis
Stream.

|                         | DM                             | Group                                         |
| ----------------------- | ------------------------------ | --------------------------------------------- |
| Stream                  | `chat:events:stream:<user_id>` | `group:events:stream:<group_id>`              |
| Cursor                  | `chat:events:last:<user_id>`   | `group:events:last:<group_id>:<user_id>`      |
| Replay on first connect | up to the last 100 entries     | **none** — cursor anchors to the newest entry |
| Cursor TTL              | ~10 minutes                    | 30 days                                       |
| Stream cap              | 5000 entries                   | 5000 entries                                  |

Practical consequences:

- **Group:** history is _not_ replayed on first connect (or after a >30 day gap);
  load history via REST (`GET /api/v1/groups/{group_id}/messages`). Reconnects
  within 30 days replay only what you missed.
- **DM:** on first connect the socket may replay recent messages from the stream;
  dedupe by `data.id`.
- Replayed frames are delivered **before** the ready frame for groups, and around
  the ready frame for DMs. Wait for `group.ready` / `chat.ready` before assuming
  catch-up is complete.
- Offline members still receive a **push notification** and a persisted
  notification row (see §9); they simply have no socket to receive the frame live.

---

## 8. Error frames

Error frames always have `"type": "error"`. Shape varies slightly between DM and
group.

### Direct messages

```json
{
  "type": "error",
  "error": "invalid_payload",
  "message": "Expected: {type:'chat.send', recipient_id:'<uuid>', body:'...'}"
}
```

| `error`                    | Cause                                                                                  |
| -------------------------- | -------------------------------------------------------------------------------------- |
| `invalid_payload`          | `chat.send` / `chat.upload_media` / `chat.read` / `chat.typing` body failed validation |
| `self_send_not_allowed`    | `chat.upload_media` with `recipient_id` == self                                        |
| `invalid_media_type`       | media type not in `image` / `video` / `file`                                           |
| `missing_media_urls`       | empty `media_urls`                                                                     |
| `invalid_media_urls`       | a URL is not a Cloudinary secure URL for this deployment                               |
| `chat.send.failed`         | persistence failed (e.g. not allowed to message recipient)                             |
| `chat.upload_media.failed` | media message persistence failed                                                       |
| `chat.read.failed`         | read update failed (conversation not found, bad `message_id`, …)                       |
| `chat.typing.failed`       | typing publish failed                                                                  |

DM handler errors are non-fatal: the socket stays open.

### Group

```json
{ "type": "error", "message": "Unknown message type: foo" }
```

| `message`                                   | Cause                                                          |
| ------------------------------------------- | -------------------------------------------------------------- |
| `Invalid JSON format`                       | inbound text was not valid JSON                                |
| `Invalid message format`                    | parsed JSON was not an object                                  |
| `Unknown message type: <type>`              | unrecognised `type`                                            |
| `Message body cannot be empty`              | `group_message` with blank body                                |
| `error: "group.message.failed"` + `message` | persistence failed (not a member, inactive group, bad mention) |

Unknown types never close the socket.

---

## 9. Non-WebSocket side effects (push & notifications)

When a message is sent while a recipient has no socket, the backend persists a
notification row and enqueues a push/mobile event. These are also useful to hook
into app-wide notification handling.

| Chat  | Notification `event_type` | Push/mobile event name  | Key payload fields                                                                                                              |
| ----- | ------------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| DM    | `chat_message`            | `chat.message.created`  | `conversation_id`, `message_id`, `sender_id`, `sender`, `sender_profile_image`, optional `media_type`/`media_urls`/`media_name` |
| Group | `group_message`           | `group.message.created` | `group_id`, `message_id`, `sender_id`, `body` (≤80 chars), optional `media_type`/`media_urls`/`media_names`                     |

Notification payloads also carry a `route` for deep-linking:
`chat.conversation` (DM) / `group.chat` (group).

Web Push registration uses the REST endpoints in the README
(`GET /api/v1/push/vapid-public-key`, `POST /api/v1/push/subscribe`).

---

## 10. Related REST endpoints

| Purpose                                                           | Endpoint                                                     |
| ----------------------------------------------------------------- | ------------------------------------------------------------ |
| DM send (fallback without socket)                                 | `POST /api/v1/chats/messages`                                |
| DM conversations                                                  | `GET /api/v1/chats/conversations`                            |
| DM messages                                                       | `GET /api/v1/chats/conversations/{conversation_id}/messages` |
| Sign chat upload                                                  | `POST /api/v1/uploads/chat/sign`                             |
| Group send                                                        | `POST /api/v1/groups/{group_id}/messages`                    |
| Group history                                                     | `GET /api/v1/groups/{group_id}/messages`                     |
| Group members (also use to verify membership before reconnecting) | `GET /api/v1/groups/{group_id}/members`                      |

---

## 11. Quick reference — every frame type

### Client → Server

| Endpoint | Types                                                                      |
| -------- | -------------------------------------------------------------------------- |
| DM       | `ping`, `chat.send`, `chat.upload_media`, `chat.read`, `chat.typing`       |
| Group    | `ping`, `group_message` (`group.message`), `group_typing` (`group.typing`) |

### Server → Client

| Endpoint | Types                                                                                                                                                                                     |
| -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DM       | `chat.ready`, `pong`, `bouwnce.system`, `user.online.snapshot`, `user.online`, `chat.send.ack`, `chat.sent`, `chat.message`, `chat.read.ack`, `chat.read.updated`, `chat.typing`, `error` |
| Group    | `group.ready`, `pong`, `group_message`, `group_message_sent`, `group_typing`, `error`                                                                                                     |

---

## 12. Client checklist

1. Open the socket with a fresh `access` token (and `group_id` for groups).
2. Wait for `chat.ready` / `group.ready` before enabling the send UI.
3. Send `ping` on an idle interval; treat `pong` as liveness.
4. On send: attach a `client_id`, render an optimistic bubble, reconcile on
   `chat.sent` / `group_message_sent`.
5. Dedupe all inbound message frames by `data.id`.
6. On group reconnect, reload history via REST and then listen for new frames.
7. If the handshake is rejected, refresh the token and (for groups) re-check
   membership before retrying with backoff.
